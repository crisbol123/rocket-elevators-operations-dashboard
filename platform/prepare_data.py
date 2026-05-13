import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
KEEP = {"ACTIVE", "PENDING_RENEWAL"}


def fmt_location(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    match = re.search(r"[A-Z]\d[A-Z]", s)
    trimmed = s[: match.start()].strip() if match else s.strip()
    parts = re.split(r"  +", trimmed)
    return ", ".join(p.title() for p in parts)


def extract_city(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    match = re.search(r"[A-Z]\d[A-Z]", s)
    trimmed = s[: match.start()].strip() if match else s.strip()
    parts = re.split(r"  +", trimmed)
    raw = parts[-1] if len(parts) > 1 else (trimmed.split()[-1] if trimmed else "")
    return raw.title()


def main() -> None:
    license_df = pd.read_csv(ROOT / "data" / "license.csv")

    print(license_df["LICENSESTATUS"].value_counts(dropna=False))

    before = len(license_df)
    license_df = license_df[license_df["LICENSESTATUS"].isin(KEEP)].reset_index(drop=True)
    print(f"\nRows after filtering: {len(license_df):,} (removed {before - len(license_df):,} rows)")

    raw_loc = license_df["LocationoftheElevatingDevice"]

    fleet = pd.DataFrame({
        "elevator_id":        license_df["ElevatingDevicesNumber"],
        "location":           raw_loc.apply(fmt_location),
        "city":               raw_loc.apply(extract_city),
        "license_number":     license_df["ElevatingDevicesLicenseNumber"],
        "license_status":     license_df["LICENSESTATUS"],
        "license_expiry_date": license_df["LICENSEEXPIRYDATE"],
    })

    out = Path(__file__).parent / "elevator_fleet.csv"
    fleet.to_csv(out, index=False)
    print(f"\nSaved {len(fleet):,} rows → {out}")


if __name__ == "__main__":
    main()
