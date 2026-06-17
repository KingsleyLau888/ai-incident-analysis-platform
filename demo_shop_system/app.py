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
    return {"status": "ok", "fault_mode": fault_mode, "service_name": SERVICE_NAME}


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
    allowed = {
        "none",
        "simple_database",
        "simple_timeout",
        "simple_auth",
        "complex_database",
        "complex_timeout",
        "complex_mixed",
    }
    if mode not in allowed:
        raise HTTPException(status_code=400, detail=f"mode must be one of {sorted(allowed)}")
    fault_mode = mode
    logger.info(f"Fault mode changed to {mode}")
    return {"fault_mode": fault_mode}


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
body{margin:0;font-family:Segoe UI,Microsoft YaHei,sans-serif;background:#f5f7fb;color:#17202a}
header{padding:22px 32px;background:#fff;border-bottom:1px solid #dce1e6;display:flex;justify-content:space-between;align-items:center}
h1{margin:0;font-size:24px}.sub{color:#66717d;margin-top:4px}.layout{display:grid;grid-template-columns:1fr 380px;gap:18px;padding:24px 32px}
.panel{background:#fff;border:1px solid #dce1e6;border-radius:8px;padding:18px}.products{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.product{border:1px solid #e2e7ed;border-radius:8px;padding:14px}.product h3{margin:0 0 8px}.price{font-size:22px;font-weight:700}.muted{color:#66717d}.hint{font-size:12px;color:#66717d;margin:4px 0 10px}
button{border:0;border-radius:5px;background:#1769aa;color:#fff;padding:9px 12px;cursor:pointer;font-weight:600}button.secondary{background:#eef2f6;color:#17202a}.simple button{background:#26834a}.complex button{background:#a96800}
.faults{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}.status{padding:12px;border-radius:6px;background:#eef5fb;margin-top:12px;min-height:52px}.ok{background:#e7f5ec}.err{background:#fbe9e9;color:#a52a2a}
.log{font-family:Consolas,monospace;font-size:12px;background:#101418;color:#d8dee4;border-radius:6px;padding:12px;height:180px;overflow:auto}
@media(max-width:900px){.layout{grid-template-columns:1fr}.products{grid-template-columns:1fr}}
</style>
</head>
<body>
<header><div><h1>Demo Shop</h1><div class="sub">用户在这里下单；工程师在 AI Incident Copilot 里看故障诊断。</div></div><a href="http://127.0.0.1:8010" target="_blank">打开 Incident 平台</a></header>
<main class="layout">
<section class="panel"><h2>商品</h2><div id="products" class="products"></div></section>
<aside class="panel">
<h2>故障注入</h2>
<div class="faults"><button class="secondary" onclick="setFault('none')">正常</button></div>
<h3>简单故障</h3>
<p class="hint">单一信号，预期走稳定 pipeline。</p>
<div class="faults simple">
<button onclick="setFault('simple_database')">简单数据库</button>
<button onclick="setFault('simple_timeout')">简单超时</button>
<button onclick="setFault('simple_auth')">简单认证</button>
</div>
<h3>复杂故障</h3>
<p class="hint">混合信号，预期自动升级 Agent。</p>
<div class="faults complex">
<button onclick="setFault('complex_database')">复杂数据库</button>
<button onclick="setFault('complex_timeout')">复杂超时</button>
<button onclick="setFault('complex_mixed')">混合故障</button>
</div>
<div id="status" class="status">准备就绪</div><h2>操作记录</h2><div id="log" class="log"></div></aside>
</main>
<script>
let selectedSku='';
const log=t=>{const box=document.querySelector('#log');box.innerHTML=`<div>${new Date().toLocaleTimeString()} ${t}</div>`+box.innerHTML};
async function loadProducts(){const r=await fetch('/api/products');const products=await r.json();if(!selectedSku&&products[0])selectedSku=products[0].sku;document.querySelector('#products').innerHTML=products.map(p=>`<div class="product"><h3>${p.name}</h3><div class="muted">SKU ${p.sku}</div><div class="price">$${p.price}</div><p class="muted">库存 ${p.stock}</p><button onclick="checkout('${p.sku}')">Checkout</button></div>`).join('')}
async function setFault(mode){const r=await fetch('/api/faults/'+mode,{method:'POST'});const v=await r.json();document.querySelector('#status').className='status';document.querySelector('#status').textContent='当前模式：'+v.fault_mode;log('fault_mode='+v.fault_mode)}
async function checkout(sku){const status=document.querySelector('#status');status.className='status';status.textContent='正在 Checkout...';log('checkout '+sku);const r=await fetch('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sku,quantity:1})});const v=await r.json();if(r.ok){status.className='status ok';status.textContent='支付成功：'+v.request_id;log('paid '+v.request_id);loadProducts()}else{status.className='status err';status.textContent='支付失败：'+v.detail;log('failed '+v.detail)}}
loadProducts();
</script>
</body>
</html>
"""
