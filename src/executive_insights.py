"""Data-derived, observational prompts for the first dashboard."""
from __future__ import annotations
import pandas as pd


def observations(channels: pd.DataFrame, devices: pd.DataFrame) -> list[dict[str, str]]:
    items = []
    eligible = channels.loc[channels.policies >= 100].dropna(subset=["ltv_cac"])
    if len(eligible) >= 2:
        best = eligible.sort_values("ltv_cac", ascending=False).iloc[0]
        rest = eligible.loc[eligible.channel != best.channel]
        benchmark = (rest.ltv * rest.policies).sum() / rest.spend.sum()
        items.append({"tag": "CAPITAL ALLOCATION", "title": f"{best.channel} leads on customer value",
                      "evidence": f"{best.ltv_cac:.1f}× modeled LTV/CAC vs {benchmark:.1f}× across the other channels.",
                      "action": "Test incremental capacity before increasing the budget. Historical averages do not measure marginal returns."})
        costly = eligible.sort_values("cac", ascending=False).iloc[0]
        cheap_weaker = eligible[(eligible.cac < costly.cac) & (eligible.ltv_cac < costly.ltv_cac)]
        if not cheap_weaker.empty:
            weaker = cheap_weaker.sort_values("ltv_cac").iloc[0]
            items.append({"tag": "UNIT ECONOMICS", "title": "A lower CAC can hide weaker value",
                          "evidence": f"{weaker.channel}: ${weaker.cac:.0f} CAC / {weaker.ltv_cac:.1f}× value. {costly.channel}: ${costly.cac:.0f} / {costly.ltv_cac:.1f}×.",
                          "action": "Compare retention and risk mix before rewarding cheaper acquisition."})
    if {"Mobile", "Desktop"}.issubset(set(devices.device_type)):
        d = devices.set_index("device_type")
        gap = d.loc["Desktop", "completion"] - d.loc["Mobile", "completion"]
        if gap > .02 and d.starts.min() >= 100:
            items.append({"tag": "PRODUCT FRICTION", "title": "Mobile quote completion trails desktop",
                          "evidence": f"{gap * 100:.1f} percentage-point gap · {d.loc['Mobile', 'completion']:.1%} mobile vs {d.loc['Desktop', 'completion']:.1%} desktop.",
                          "action": "Segment by acquisition source, then test a shorter mobile quote flow. This gap is observational."})
    return items[:3]
