from app.services.rrf import reciprocal_rank_fusion


def test_rrf_rewards_results_that_rank_well_in_multiple_lists():
    sparse_ranked = [("a", 0.9), ("b", 0.8), ("c", 0.7)]
    dense_ranked = [("b", 0.95), ("a", 0.6), ("d", 0.5)]

    fused = reciprocal_rank_fusion(
        [sparse_ranked, dense_ranked],
        key=lambda item: item[0],
        k=60,
    )

    assert [result.item[0] for result in fused] == ["a", "b", "c", "d"]
    assert fused[0].score > fused[2].score
