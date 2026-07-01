from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from integrations.python_logging_handler import IncidentPlatformHandler


APP_TITLE = "Demo Shop System"
SERVICE_NAME = os.getenv("SHOP_SERVICE_NAME", "demo-shop-checkout-service")
DATABASE_PATH = Path(
    os.getenv("SHOP_DATABASE_PATH", str(Path(tempfile.gettempdir()) / "demo_shop.db"))
)
LOG_FORWARDING_ENABLED = os.getenv("SHOP_LOG_FORWARDING_ENABLED", "1").lower() in {
    "1",
    "true",
    "yes",
}

app = FastAPI(title=APP_TITLE)
fault_mode = "none"

logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.handlers.clear()
if LOG_FORWARDING_ENABLED:
    platform_handler = IncidentPlatformHandler(
        platform_url=os.getenv("INCIDENT_API_URL", "http://127.0.0.1:8000"),
        service_name=SERVICE_NAME,
        timeout=10.0,
    )
    platform_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(platform_handler)
logger.addHandler(logging.StreamHandler())


PRODUCTS = [
    {"sku": "keyboard-pro", "name": "Keyboard Pro", "price": 129, "stock": 8},
    {"sku": "noise-cancel-headset", "name": "Noise Cancel Headset", "price": 219, "stock": 5},
    {"sku": "usb-c-dock", "name": "USB-C Dock", "price": 89, "stock": 12},
]

FAULT_LABELS = {
    "none": "正常运行",
    "simple_database": "数据库降级",
    "simple_timeout": "支付超时",
    "simple_auth": "认证异常",
    "complex_database": "复杂数据库故障",
    "complex_timeout": "复杂支付超时",
    "complex_mixed": "认证 + 超时混合故障",
}


@app.on_event("startup")
def startup() -> None:
    init_database()


def init_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                sku TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                stock INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                sku TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for product in PRODUCTS:
            connection.execute(
                """
                INSERT INTO products (sku, name, price, stock)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    name=excluded.name,
                    price=excluded.price,
                    stock=max(products.stock, excluded.stock)
                """,
                (product["sku"], product["name"], product["price"], product["stock"]),
            )
        connection.commit()


def connect_database() -> sqlite3.Connection:
    if fault_mode == "complex_database":
        raise sqlite3.OperationalError("DBConnectionTimeout while connecting to shop-primary")
    return sqlite3.connect(DATABASE_PATH)


@app.get("/", response_class=HTMLResponse)
def shop_frontend() -> str:
    return SHOP_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "fault_mode": fault_mode,
        "fault_label": FAULT_LABELS[fault_mode],
        "service_name": SERVICE_NAME,
    }


@app.get("/api/products")
def list_products() -> list[dict]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            "SELECT sku, name, price, stock FROM products ORDER BY sku"
        ).fetchall()
    return [
        {"sku": sku, "name": name, "price": price, "stock": stock}
        for sku, name, price, stock in rows
    ]


@app.post("/api/faults/{mode}")
def set_fault(mode: str) -> dict[str, str]:
    global fault_mode
    if mode not in FAULT_LABELS:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(FAULT_LABELS)}")
    fault_mode = mode
    logger.info(f"Runtime condition changed to {FAULT_LABELS[mode]} ({mode})")
    return {"fault_mode": fault_mode, "fault_label": FAULT_LABELS[mode]}


@app.post("/api/checkout")
def checkout(payload: dict) -> dict[str, str]:
    sku = str(payload.get("sku") or "")
    quantity = int(payload.get("quantity") or 1)
    request_id = uuid4().hex[:8]
    logger.info(f"Checkout started request_id={request_id} sku={sku} quantity={quantity}")

    if fault_mode == "simple_auth":
        logger.error("Authentication failed while creating checkout session")
        logger.error("Customer token rejected by auth middleware")
        logger.error("Checkout session blocked by auth service")
        raise HTTPException(status_code=401, detail="authentication failed")

    if fault_mode == "simple_timeout":
        logger.error("Payment provider timeout during checkout")
        logger.error("Payment provider timeout retry exhausted")
        logger.error("Payment provider timeout blocked checkout")
        raise HTTPException(status_code=504, detail="payment provider timeout")

    if fault_mode == "simple_database":
        logger.error("shop-primary database unavailable for checkout write")
        logger.error("shop-primary database rejected order creation")
        logger.error("shop-primary database unavailable during checkout")
        raise HTTPException(status_code=500, detail="database unavailable")

    if fault_mode == "complex_mixed":
        logger.error("Unauthorized checkout token rejected by auth middleware")
        logger.error("Payment provider request timed out after auth retry")
        logger.error("Checkout API returned 500 after auth dependency timeout")
        raise HTTPException(status_code=500, detail="mixed checkout failure")

    if fault_mode == "complex_timeout":
        logger.info("Inventory reserved before payment provider call")
        time.sleep(1)
        logger.error("Payment provider request timed out after 30 seconds")
        logger.error("Checkout payment retry exhausted for payment-provider-primary")
        logger.error("Checkout API returned 500 after upstream payment timeout")
        raise HTTPException(status_code=504, detail="payment provider timeout")

    try:
        with connect_database() as connection:
            row = connection.execute(
                "SELECT stock FROM products WHERE sku = ?",
                (sku,),
            ).fetchone()
            if row is None:
                logger.warning(f"Checkout rejected unknown sku={sku}")
                raise HTTPException(status_code=404, detail="product not found")
            if row[0] < quantity:
                logger.warning(f"Checkout rejected insufficient inventory sku={sku}")
                raise HTTPException(status_code=409, detail="insufficient inventory")

            order_id = uuid4().hex
            connection.execute(
                "UPDATE products SET stock = stock - ? WHERE sku = ?",
                (quantity, sku),
            )
            connection.execute(
                "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?)",
                (order_id, sku, quantity, "paid"),
            )
            connection.commit()
    except sqlite3.OperationalError as exc:
        logger.error(str(exc))
        logger.error("Order creation failed because shop-primary database is unavailable")
        logger.error("Checkout API returned 500 after database write failure")
        raise HTTPException(status_code=500, detail="database unavailable") from exc

    logger.info(f"Inventory reserved sku={sku} quantity={quantity}")
    logger.info(f"Order created and paid request_id={request_id} sku={sku}")
    return {"status": "paid", "request_id": request_id}


SHOP_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Demo Shop</title>
<style>
:root{--bg:#f5f7fb;--panel:#fff;--ink:#17202a;--muted:#66717d;--line:#dce1e6;--blue:#1769aa;--green:#26834a;--red:#c43d3d;--amber:#a96800}
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,Microsoft YaHei,sans-serif;background:var(--bg);color:var(--ink);font-size:14px;letter-spacing:0}
header{padding:18px 28px;background:#fff;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:18px}
h1{margin:0;font-size:24px}h2{font-size:18px;margin:0 0 12px}h3{font-size:14px;margin:18px 0 8px}.sub{color:var(--muted);margin-top:4px}
a{color:var(--blue);text-decoration:none}.layout{display:grid;grid-template-columns:1fr 360px;gap:18px;padding:22px 28px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;padding:18px}
.products{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.product{border:1px solid #e2e7ed;border-radius:8px;padding:14px;display:grid;gap:8px}.product h3{font-size:17px;margin:0}.price{font-size:22px;font-weight:700}
.muted{color:var(--muted)}.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;background:#eef2f6;color:#384453;padding:4px 9px;font-size:12px}.pill.ok{background:#e7f5ec;color:var(--green)}.pill.bad{background:#fbe9e9;color:var(--red)}
button{border:0;border-radius:6px;background:var(--blue);color:#fff;padding:9px 12px;cursor:pointer;font-weight:700}button.secondary{background:#eef2f6;color:#17202a}.faults{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.faults button{background:#304a68}.faults.simple button{background:#3f7d56}.faults.complex button{background:#9b6416}
.status{padding:13px;border-radius:7px;background:#eef5fb;margin-top:12px;min-height:58px}.status.ok{background:#e7f5ec}.status.err{background:#fbe9e9;color:var(--red)}.status strong{display:block;margin-bottom:4px}
.activity{font-family:Consolas,monospace;font-size:12px;background:#101418;color:#d8dee4;border-radius:6px;padding:12px;height:190px;overflow:auto}.activity div{padding:4px 0;border-bottom:1px solid #252b31}
.note{font-size:12px;color:var(--muted);line-height:1.55;margin:6px 0 12px}.role{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}.role div{border:1px solid var(--line);border-radius:7px;padding:12px;background:#fafbfc}
@media(max-width:1000px){.layout{grid-template-columns:1fr}.products{grid-template-columns:1fr}.role{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div>
    <h1>Demo Shop</h1>
    <div class="sub">普通用户只负责下单；后台状态异常时，AI Incident Copilot 自动接收日志并诊断。</div>
  </div>
  <div>
    <span id="runtime-pill" class="pill ok">正常运行</span>
    <a href="http://127.0.0.1:8010" target="_blank">打开 Incident 平台</a>
  </div>
</header>
<main class="layout">
  <section class="panel">
    <div class="role">
      <div><b>用户视角</b><p class="note">用户只看到商品和 checkout，不知道系统内部是否有数据库、认证或支付依赖异常。</p></div>
      <div><b>工程师视角</b><p class="note">错误日志会被发送到 Incident Copilot，平台自动创建 Incident、分析证据并展示 Trace。</p></div>
    </div>
    <h2>商品</h2>
    <div id="products" class="products"></div>
  </section>
  <aside class="panel">
    <h2>运行状态控制台</h2>
    <p class="note">这是演示用的后台控制台，用来模拟真实系统里的依赖异常；普通用户不会看到这里。</p>
    <div class="faults"><button class="secondary" onclick="setFault('none')">恢复正常</button></div>
    <h3>单一故障</h3>
    <div class="faults simple">
      <button onclick="setFault('simple_database')">数据库降级</button>
      <button onclick="setFault('simple_timeout')">支付超时</button>
      <button onclick="setFault('simple_auth')">认证异常</button>
    </div>
    <h3>复杂故障</h3>
    <div class="faults complex">
      <button onclick="setFault('complex_database')">数据库连接中断</button>
      <button onclick="setFault('complex_timeout')">支付链路超时</button>
      <button onclick="setFault('complex_mixed')">认证 + 超时混合</button>
    </div>
    <div id="status" class="status"><strong>准备就绪</strong><span>请选择商品并 checkout。</span></div>
    <h2 style="margin-top:18px">用户操作记录</h2>
    <div id="log" class="activity"></div>
  </aside>
</main>
<script>
let selectedSku='';
const labels={
  none:'正常运行',simple_database:'数据库降级',simple_timeout:'支付超时',simple_auth:'认证异常',
  complex_database:'复杂数据库故障',complex_timeout:'复杂支付超时',complex_mixed:'认证 + 超时混合故障'
};
const log=t=>{const box=document.querySelector('#log');box.innerHTML=`<div>${new Date().toLocaleTimeString()} ${t}</div>`+box.innerHTML};
function setStatus(kind,title,body){const el=document.querySelector('#status');el.className='status '+kind;el.innerHTML=`<strong>${title}</strong><span>${body}</span>`}
async function loadProducts(){
  const r=await fetch('/api/products');const products=await r.json();
  if(!selectedSku&&products[0])selectedSku=products[0].sku;
  document.querySelector('#products').innerHTML=products.map(p=>`<div class="product"><h3>${p.name}</h3><div class="muted">SKU ${p.sku}</div><div class="price">$${p.price}</div><p class="muted">库存 ${p.stock}</p><button onclick="checkout('${p.sku}')">Checkout</button></div>`).join('');
}
async function setFault(mode){
  const r=await fetch('/api/faults/'+mode,{method:'POST'});const v=await r.json();
  const pill=document.querySelector('#runtime-pill');pill.textContent=v.fault_label;pill.className='pill '+(mode==='none'?'ok':'bad');
  setStatus('', '运行状态已切换', v.fault_label);
  log('runtime='+v.fault_label);
}
async function checkout(sku){
  setStatus('', '正在 Checkout...', sku);log('checkout '+sku);
  const r=await fetch('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sku,quantity:1})});
  const v=await r.json();
  if(r.ok){setStatus('ok','支付成功',v.request_id);log('paid '+v.request_id);loadProducts()}
  else{setStatus('err','支付失败',v.detail);log('failed '+v.detail)}
}
loadProducts();
</script>
</body>
</html>
"""
