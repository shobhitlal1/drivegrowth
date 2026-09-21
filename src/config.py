"""Portable paths and explicit synthetic business assumptions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "processed" / "drivegrowth.duckdb"
SEED = 20260921
N_CUSTOMERS = 500_000
START_DATE = "2024-09-01"
END_DATE = "2026-08-31"
CHANNELS = ["Google Search", "Meta Ads", "Affiliate Partners", "Organic Search",
            "Referral", "Direct", "TikTok / Social", "Comparison Websites"]
CHANNEL_WEIGHTS = [.25, .17, .12, .14, .09, .08, .07, .08]
STATES = ["CA", "TX", "FL", "NY", "NJ", "PA", "IL", "OH", "GA", "NC", "AZ", "WA"]
STATE_WEIGHTS = [.18, .16, .13, .10, .05, .06, .06, .06, .06, .05, .04, .05]
STATE_PREMIUM = [1.20, 1.09, 1.30, 1.25, 1.13, .92, .97, .83, 1.04, .85, .95, .90]
# Per registered visitor. Includes content, referral-program and brand operating spend.
CHANNEL_COST = [25.0, 7.0, 15.0, 8.0, 9.5, 6.5, 4.5, 18.0]
START_RATE = [.79, .53, .70, .74, .85, .76, .45, .77]
COMPLETE_RATE = [.78, .65, .73, .80, .87, .80, .59, .76]
PURCHASE_RATE = [.52, .32, .48, .49, .61, .48, .29, .53]
MONTHLY_CHURN = [.012, .035, .024, .010, .007, .012, .050, .036]
RENEWAL_PROBABILITY = [.84, .66, .75, .86, .91, .84, .58, .68]
CARRIER_NAMES = ["Northstar Mutual", "Juniper Assurance", "Harbor Insurance",
                 "Summit Auto", "Cedar & Co."]
DISCLAIMER = ("This project uses synthetically generated customer-level data designed to "
              "simulate realistic insurance marketplace behavior. It is not affiliated with "
              "or based on proprietary data from any insurance company.")
