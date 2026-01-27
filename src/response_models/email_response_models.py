from typing import List, Literal

from pydantic import BaseModel, Field

from definitions.enums import FiscalTopic

class EmailClassifierResponse(BaseModel):
    should_respond: bool = Field(
        ...,
        description="Of er wel of niet op een e-mail gereageerd moet worden"
    )
    reasoning: str = Field(
        ...,
        description="De reden waarom er wel of niet op een e-mail gereageerd moet worden"
    )
    fiscal_topic: List[FiscalTopic] = Field(
        ...,
        description=(
            "Lijst van belastingonderwerpen die relevant zijn voor de vraag. Mogelijke waarden per onderwerp: "
            "OB (Omzetbelasting/BTW), IB (Inkomstenbelasting), VPB (Vennootschapsbelasting). "
            f"Mogelijke waarden: {', '.join(FiscalTopic.get_values())}. "
            "Meerdere onderwerpen kunnen geselecteerd worden als de vraag betrekking heeft op verschillende belastingsoorten. "
            "Wanneer de vraag niet relevant is voor een fiscale en boekhoudkundige topic, geef dan 'Onbekend' als fiscal_topic. "
            "Wanneer je uit de context duidelijk kunt afleiden dat de vraag gaat over meerdere belastingsoorten, geef dan alle relevante belastingsoorten in de lijst. "
            "Er is 1 mogelijk edgecase. Het is mogelijk dat een persoon vanuit de chatgeschiedenis een vraag stelt over verschillende categorieën. "
            "Echter kan hierna een reactie gegeven worden zoals 'Bedankt', 'Ok', of iets zegt wat niet per se een vraag is. "
            "Omdat de chatgeschiedenis aangeeft dat het over een bepaald fiscaal onderwerp gaat wil dit niet zeggen dat dat in dit geval ook zo is. "
            "In dat geval geef dan 'Onbekend' als fiscal_topic. Waarom is dit? De fiscal_topic wordt gebruikt om aan te geven waar we in onze interne database gaan zoeken; "
            "onbekend in dit geval betekent dat we ook niet hoeven zoeken en snel een reactie kunnen geven."
        ),
        examples=[
            ["Omzetbelasting"],
            ["Inkomstenbelasting"],
            ["Vennootschapsbelasting"],
            ["Omzetbelasting", "Inkomstenbelasting"],
            ["Omzetbelasting", "Inkomstenbelasting", "Vennootschapsbelasting"],
            ["Onbekend"]
        ]
    )
    year: List[int] = Field(
        ...,
        description=(
            "Lijst van jaren waarop de vraag betrekking heeft. Bepaal de relevante belastingjaren op basis van de gebruikersvraag. "
            "STANDAARDWAARDEN PER BELASTINGSOORT: BTW → 2025, IB/VPB → 2024. "
            "RICHTLIJNEN: "
            "1) Als expliciet jaren genoemd worden in de vraag (bijv. '2025', '25', 'Dit jaar'), neem deze jaren op in de lijst. "
            "2) Voor BTW of recente aangiftes zonder specifiek jaar, gebruik het huidige kalenderjaar (2025). "
            "3) Voor inkomstenbelasting (IB) of vennootschapsbelasting (VPB) zonder specifiek jaar, gebruik het voorgaande jaar (2024). "
            "4) Bij twijfel of onduidelijkheid, check eerst of de vraag over BTW (2025) of IB/VPB (2024) gaat. "
            "5) Als de vraag betrekking heeft op meerdere jaren, voeg alle relevante jaren toe aan de lijst. "
            "Let op impliciete verwijzingen naar jaren, zoals 'dit jaar', 'vorig jaar', 'volgend jaar', 'dit kwartaal', etc."
        ),
        examples=[
            [2025],
            [2024],
            [2023],
            [2024, 2025],
            [2023, 2024, 2025]
        ]
    )
    vector_query: str = Field(
        ...,
        description=(
            "Een compacte, objectieve zoekopdracht die de fiscale kern van de gebruikersvraag samenvat, bedoeld voor vector search. "
            "Deze string wordt ge-embed en gebruikt om semantisch relevante documenten te vinden in de vector store. "
            "RICHTLIJNEN: "
            "1) Behoud alle belangrijke fiscale termen en entiteiten (bijv. belastingsoorten, structuren, regelingen), maar laat jaartallen weg. "
            "2) Gebruik een neutrale, zakelijke toon - vermijd persoonlijke voornaamwoorden ('ik', 'je') of vraagvormen. "
            "3) Houd het compact: ongeveer 10-20 woorden met semantische precisie. "
            "4) Vermijd overbodige context; richt je op de kern van het fiscale of boekhoudkundige probleem. "
            "5) Integreer impliciete context (zoals herkomst of gevolgen) als die essentieel is voor betekenisvolle matching. "
            "6) Denk in zoekopdrachten zoals in een juridische of fiscale kennisbank."
        ),
        examples=[
            "btw tarieven en uitzonderingen horeca",
            "verliesverrekening vennootschapsbelasting carry back forward regels",
            "verwerking lidmaatschapscontributie bij beëindiging lidmaatschap artikel 35",
            "auto zakelijk versus privé gebruik fiscale gevolgen",
            "aftrekbaarheid huurkosten zzp werkruimte privéwoning",
            "voorwaarden innovatiebox softwareontwikkeling vpb",
            "belastingplicht anbi stichting commerciële activiteiten",
            "bezwaar naheffingsaanslag btw suppletie boete",
            "deelnemingsvrijstelling buitenlandse dochtermaatschappij",
            "vrijstelling erfbelasting bij ANBI schenking",
            "groet bericht"
        ]
    )
    confidence: Literal["laag", "gemiddeld", "hoog"] = Field(
        ...,
        description="De confidence in de classificatie"
    )

class EmailReplyRequest(BaseModel):
    subject: str = Field(description="Onderwerp van de e-mail")
    body: str = Field(description="Inhoud van de e-mail")
    sender_name: str = Field(default="", description="Naam van de e-mailafzender")
    sender_email: str = Field(default="", description="E-mailadres van de e-mailafzender")
    recipient_name: str = Field(default="", description="Naam van de persoon die het antwoord geeft (te gebruiken in de ondertekening)")


class EmailReplyResponse(BaseModel):
    answer: str = Field(description="Gegenereerde e-mailantwoord in professioneel Nederlands")
    tone: str = Field(description="Gedetecteerde toon van de originele e-mail (formeel/informeel/dringend/vriendelijk)")
    reasoning: str = Field(description="Korte uitleg van de antwoordstrategie en de belangrijkste behandelde punten")