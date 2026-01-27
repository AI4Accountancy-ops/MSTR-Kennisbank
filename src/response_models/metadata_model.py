from pydantic import BaseModel, Field

import definitions.enums as enums


class MetaData(BaseModel):
    information_type: enums.InformationType.get_typing() = Field(
        description="Het type informatie dat in het document wordt besproken.",
        examples=[
            "informatief/conceptueel",
            "procedureel",
            "berekening",
            "compliance",
            "juridisch",
            "casusgericht",
            "actuele ontwikkelingen"
        ]
    )
    
    # Replace fiscal_topic with individual boolean fields
    is_algemeen: bool = Field(default=False, description="Algemeen fiscaal onderwerp")
    is_autobelastingen: bool = Field(default=False, description="Autobelastingen")
    is_dividendbelasting: bool = Field(default=False, description="Dividendbelasting")
    is_formeel_belastingrecht: bool = Field(default=False, description="Formeel belastingrecht")
    is_inkomstenbelasting: bool = Field(default=False, description="Inkomstenbelasting")
    is_lokale_heffingen: bool = Field(default=False, description="Lokale heffingen")
    is_loonbelasting: bool = Field(default=False, description="Loonbelasting")
    is_omzetbelasting: bool = Field(default=False, description="Omzetbelasting")
    is_pensioen_en_lijfrente: bool = Field(default=False, description="Pensioen en lijfrente")
    is_schenken_en_erven: bool = Field(default=False, description="Schenken en erven")
    is_sociale_verzekeringen: bool = Field(default=False, description="Sociale verzekeringen")
    is_vennootschapsbelasting: bool = Field(default=False, description="Vennootschapsbelasting")
    is_wet_op_belastingen_van_rechtsverkeer: bool = Field(default=False, description="Wet op belastingen van rechtsverkeer")
    
    target_group: enums.TargetGroup.get_typing() = Field(
        description="De doelgroep waarvoor de inhoud bedoeld is.",
        examples=["Bedrijven", "Particulieren", "Overheid"]
    )
