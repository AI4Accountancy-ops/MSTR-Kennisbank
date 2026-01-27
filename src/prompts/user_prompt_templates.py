tax_query_user_prompt = """
<tone_of_voice>
{tone_of_voice}
</tone_of_voice>

<chat_geschiedenis>
{chat_history}
</chat_geschiedenis>

<bronnen>
<chunks>
{chunks_str}
</chunks>

<web_sources>
{sources_block}
</web_sources>
</bronnen>

<vraag>
{query}
</vraag>

(__Let op: zorg in je antwoord altijd voor een duidelijke structuur en opmaak in markdown en gebruik horizontale lijnen (---) om secties te scheiden.__)
"""

web_search_user_prompt = """
<tone_of_voice>
{tone_of_voice}
</tone_of_voice>

<chat_geschiedenis>
{chat_history}
</chat_geschiedenis>

<vraag>
{question}
</vraag>

<bronnen>
{sources_block}
</bronnen>

Instructies:
- Beantwoord helder, actueel en in het Nederlands in de opgegeven schrijfstijl.
- Gebruik uitsluitend de informatie uit <bronnen>; citeer of noem GEEN links in je antwoord.
- Vul in het modelveld `sources` de SUBSET van URL-strings uit <bronnen> die je daadwerkelijk hebt gebruikt.

(__Let op: zorg in je antwoord altijd voor een duidelijke structuur en opmaak in markdown en gebruik horizontale lijnen (---) om secties te scheiden.__)
"""

search_query_user_prompt = """
<vraag>
{question}
</vraag>

<chat_geschiedenis>
{chat_history}
</chat_geschiedenis>

Geef alleen de uiteindelijke zoekopdracht.
"""

## TODO[SM]: Enhance prompt for first llm call
question_user_prompt = """
<vraag>
{query}
</vraag>

<chat_geschiedenis>
{chat_history}
</chat_geschiedenis>
"""

chunk_metadata_user_prompt = """
Analyseer de inhoud van deze tekst en bepaal de volgende aspecten:
1. Welke fiscale onderwerpen relevant zijn
2. Welk type informatie dit is
3. Voor welke doelgroep de inhoud bedoeld is

Geef je analyse terug in het volgende JSON-formaat:
    ```
    {{
        # Fiscal topics - zet voor elk onderwerp "true" als het van toepassing is, anders "false"
        "is_algemeen": false,                      # Is de inhoud gerelateerd aan Algemeen fiscaal onderwerp?
        "is_autobelastingen": false,               # Is de inhoud gerelateerd aan Autobelastingen?
        "is_dividendbelasting": false,             # Is de inhoud gerelateerd aan Dividendbelasting?
        "is_formeel_belastingrecht": false,        # Is de inhoud gerelateerd aan Formeel belastingrecht?
        "is_inkomstenbelasting": false,            # Is de inhoud gerelateerd aan Inkomstenbelasting?
        "is_lokale_heffingen": false,              # Is de inhoud gerelateerd aan Lokale heffingen?
        "is_loonbelasting": false,                 # Is de inhoud gerelateerd aan Loonbelasting?
        "is_omzetbelasting": false,                # Is de inhoud gerelateerd aan Omzetbelasting?
        "is_pensioen_en_lijfrente": false,         # Is de inhoud gerelateerd aan Pensioen en lijfrente?
        "is_schenken_en_erven": false,             # Is de inhoud gerelateerd aan Schenken en erven?
        "is_sociale_verzekeringen": false,         # Is de inhoud gerelateerd aan Sociale verzekeringen?
        "is_vennootschapsbelasting": false,        # Is de inhoud gerelateerd aan Vennootschapsbelasting?
        "is_wet_op_belastingen_van_rechtsverkeer": false, # Is de inhoud gerelateerd aan Wet op belastingen van rechtsverkeer?
        
        # Type informatie
        "information_type": "",                    # Het type informatie dat wordt besproken (bijv. "informatief/conceptueel", "procedureel", "berekening", "compliance", "juridisch", "casusgericht", "actuele ontwikkelingen")

        # Doelgroep
        "target_group": []                         # De doelgroep(en) waarvoor de inhoud bedoeld is (bijv. ["Bedrijven"], ["Particulieren"], ["Bedrijven", "Particulieren"])
    }}
    ```
Inhoud:
<context_inhoud>
{content}
</context_inhoud>
"""

extra_sources_needed_user_prompt = """
<vraag>
{query}
</vraag>

<chat_geschiedenis>
{chat_history}
</chat_geschiedenis>

<bronnen>
{chunks_str}
</bronnen>
"""

email_classifier_user_prompt = """
<tone_of_voice>
Professioneel en vriendelijk
</tone_of_voice>

<email_context>
<afzender>{sender_info}</afzender>
<onderwerp>{subject}</onderwerp>
<inhoud>
{body}
</inhoud>
</email_context>
{recipient_info}
"""