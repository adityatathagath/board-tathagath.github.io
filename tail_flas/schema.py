from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class Record:
    as_of_date: str
    level: str               # EM / Region / Country
    region: Optional[str]    # APAC, EEMEA, LatAm, etc.
    country: Optional[str]
    asset_class: str         # Equity / Bond / Bond (Local) / Bond (Hard)
    measure: str             # WoW, 4W, YTD, etc.
    value: float             # numeric value (USD mn)
    unit: Optional[str]      # USD mn
    source_pdf: str          # filename
    meta: Optional[Dict]