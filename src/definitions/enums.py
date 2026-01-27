from enum import Enum
from typing import List, Literal


class CustomEnum(Enum):

    @classmethod
    def get_values(cls) -> List[str]:
        return list(v.value for v in cls.__members__.values())

    @classmethod
    def get_typing(cls):
        typing = List[Literal[tuple(cls.get_values())]]
        return typing


class Metadata(Enum):
    BRON_URL: str | None = "source_url"
    JAARTAL: int | None = "jaartal"
    TYPE_VRAAG: str | None = "type_vraag"
    ONDERWERP: str | None = "onderwerp"
    AANVULLENDE_METADATA: str | None = "aanvullende_metadata"
    DOELGROEP: str | None = "doelgroep"
    BRON: str | None = "bron"


class QuestionType(CustomEnum):
    BELASTING: str = "belasting"
    ONBEKEND: str = "onbekend"


class InformationType(CustomEnum):
    INFORMATIEF: str = "informatief/conceptueel"
    PROCEDUREEL: str = "procedureel"
    BEREKENING: str = "berekening"
    BELASTING: str = "belasting"
    COMPLIANCE: str = "compliance"
    JURIDISCH: str = "juridisch"
    CASUSGERICHT: str = "casusgericht"
    ACTUELE_ONTWIKKELINGEN: str = "actuele ontwikkelingen"


class Year(CustomEnum):
    JAAR_2019: int = 2019
    JAAR_2020: int = 2020
    JAAR_2021: int = 2021
    JAAR_2022: int = 2022
    JAAR_2023: int = 2023
    JAAR_2024: int = 2024
    JAAR_2025: int = 2025


class DataCategory(CustomEnum):
    PRIMAIRE: str = "primaire"
    COMMENTAAR: str = "commentaar"
    PRAKTISCH_ADVIES: str = "praktisch advies"
    JURIDISCHE_BEGELEIDING: str = "juridische begeleiding"


class FiscalTopic(CustomEnum):
    ALGEMEEN: str = "Algemeen"
    AUTOBELASTINGEN: str = "Autobelastingen"
    DIVIDENDBELASTING: str = "Dividendbelasting"
    FORMEEL_BELASTINGRECHT: str = "Formeel belastingrecht"
    INKOMSTENBELASTING: str = "Inkomstenbelasting"
    LOKALE_HEFFINGEN: str = "Lokale heffingen"
    LOONBELASTING: str = "Loonbelasting"
    OMZETBELASTING: str = "Omzetbelasting"
    PENSIOEN_EN_LIJFRENTEN: str = "Pensioen en lijfrente"
    SCHEKEN_EN_ERVEN: str = "Schenken en erven"
    SOCIELE_VERZEKERINGEN: str = "Sociale verzekeringen"
    VENNOOTSCHAPSBELASTING: str = "Vennootschapsbelasting"
    WET_OP_BELASTINGEN_VAN_RECHTSVERKEER: str = "Wet op belastingen van rechtsverkeer"
    ONBEKEND: str = "Onbekend"


class AdditionalMetadata(CustomEnum):
    BELASTINGDIENST: str = "Belastingdienst"
    WETGEVING: str = "Wetgeving"
    PROCEDURE: str = "Procedure"
    COMPLIANCE: str = "Compliance"


class TargetGroup(CustomEnum):
    BEDRIJVEN: str = "Bedrijven"
    PARTICULIEREN: str = "Particulieren"
    OVERHEID: str = "Overheid"


class Source(CustomEnum):
    BELASTINGDIENST: str = "Belastingdienst"
    WETTEN_OVERHEID: str = "Wetten overheid"
    INTERNE_INFORMATIE: str = "Interne informatie"
    INTERNATIONALE_BRONNEN: str = "Internationale bronnen (OESO en EU wetgeving)"
    NEXTENS: str = "Nextens"
    NEXTENS_FISCALE_CIJFER: str = "Nextens fiscale cijfer"
    NEXTENS_BESLUITEN: str = "Nextens besluiten"
    NEXTENS_ONDERWERPEN: str = "Nextens onderwerpen"
    NEXTENS_ALMANAKKEN: str = "Nextens almanakken"
    NEXTENS_WETTEN: str = "Nextens wetten"
    INDICATOR: str = "Indicator"
    MFAS: str = "MFAS"


class ModerationCategory(CustomEnum):
    HATE: str = "haat"
    SELF_HARM: str = "zelfbeschadiging"
    SEXUAL: str = "seksueel"
    VIOLENCE: str = "geweld"
    NONE: str = "None"


class ModerationSeverity(CustomEnum):
    LOW: str = "laag"
    MEDIUM: str = "gemiddeld"
    HIGH: str = "hoog"
    SAFE: str = "veilig"


class FeedbackCategory(str, Enum):
    FEATURE_REQUEST = "Feature Aanvragen"
    BUG = "Error/Bug Rapporteren"
    QUALITY_ISSUE = "Kwaliteitsprobleem"
    UI_UX = "UI/UX problemen"
    OTHER = "Anders"

class ReasoningEffort(CustomEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Model(CustomEnum):
    O1 = "o1"
    O3_MINI = "o3-mini-EU"

class ToggleVectorSearch(CustomEnum):
    ON = "vector-search-on"