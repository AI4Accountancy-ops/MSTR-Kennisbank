from typing import List, Literal

from pydantic import BaseModel, Field

from definitions.enums import ModerationCategory, ModerationSeverity, FiscalTopic


class ChunkInfo(BaseModel):
    chunk_id: str = Field(..., description="Unieke ID van de bron (chunk)")
    used: bool = Field(..., description="Of deze bron (chunk) wordt gebruikt om de vraag te beantwoorden. 'True' wanneer deze bron relevant is geweest voor het antwoord.")

class TaxQueryResponse(BaseModel):
    answer: str = Field(..., description="Het antwoord op de vraag van de gebruiker, geformatteerd in Markdown.")
    chunks: List[ChunkInfo] = Field(..., description="Lijst van bronnen die gerelateerd zijn aan deze vraag")

class SearchQueryResponse(BaseModel):
    search_query: str = Field(
        ...,
        description=(
            "Eén enkele, geoptimaliseerde webzoekopdracht (één regel, geen uitleg). "
            "Gebruik duidelijke NL-termen waar passend; behoud eigennamen en vakjargon. "
            "Zet vaste woordgroepen tussen dubbele rechte aanhalingstekens (\"...\"). "
            "Gebruik operatoren wanneer zinvol: site:, filetype:, intitle:, OR (met max. 1–2 synoniemen), "
            "min-teken voor uitsluitingen (-jobs, -reddit), en eventueel jaartal of jaarbereik (YYYY..YYYY) "
            "bij actuele/recente vragen. "
            "Vermijd stopwoorden, overmatige OR-ketens, onnodige wildcards, dubbele spaties en smart quotes. "
            "Geen nieuwe regels, geen codefences, geen extra tekst."
        ),
        examples=[
            'btw tarieven 2025 site:belastingdienst.nl',
            'inkomstenbelasting aftrekposten 2024 site:belastingdienst.nl OR site:rijksoverheid.nl',
            'vennootschapsbelasting verliesverrekening 2025 site:belastingdienst.nl filetype:pdf',
            'btw verlegd bouwsector 2025 intitle:btw site:belastingdienst.nl',
            'auto van de zaak bijtelling (2024 OR 2025) site:belastingdienst.nl',
            '"belastingplan 2025" Kamerbrief site:tweedekamer.nl',
            'AVG boetebeleid 2025 samenvatting site:autoriteitpersoonsgegevens.nl -consultancy',
            'klimaatverandering Nederland zeespiegel 2020..2025 site:knmi.nl -opinie',
            'laptop 14 inch 32GB RAM vergelijking 2025 -reviewblog -affiliate',
            'verwerkersovereenkomst voorbeeld 2025 filetype:docx site:autoriteitpersoonsgegevens.nl',
            'STAP-budget vervangers 2025 Nederland site:rijksoverheid.nl',
            '"NIS2" implementatie mkb Nederland 2024..2025 site:rijksoverheid.nl OR site:government.nl',
            'PFAS factsheet site:rivm.nl filetype:pdf',
            '"Azure OpenAI Whisper" diarization Python site:github.com -issues -jobs',
            'maatwerk AI oplossingen OR "AI consultancy" Nijmegen site:mstr.nl'
        ]
    )

## TODO[SM]: Enhance response model
class QuestionFiscalTopicYear(BaseModel):
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

class ExtraSourcesNeeded(BaseModel):
    extra_sources_needed: bool = Field(
        ...,
        description="Of de gebruiker extra bronnen nodig heeft om de vraag te beantwoorden. 'True' wanneer de gebruiker extra bronnen nodig heeft om de vraag te beantwoorden. 'False' wanneer de gebruiker geen extra bronnen nodig heeft om de vraag te beantwoorden."
    )
