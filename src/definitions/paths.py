class Paths:

    def __init__(self):
        # Base paths
        self.src = 'src'
        self.assets = 'assets'

        # Main folder for scraped documents
        self.scraped_documents = 'scraped_documents'

        # CSS folder
        self.css = f'{self.assets}/css'

        # CSS folder files
        self.styling = f'{self.css}/styling.css'
        self.custom_tabs = f'{self.css}/custom_tabs.css'

        # Html_templates folder
        self.html_templates = f'{self.assets}/html_templates'

        # Html_templates folder files
        self.chatbox_template = f'{self.html_templates}/chatbox_template.html'

        # Avatar images
        self.user_avatar = f'{self.images}/person-user.svg'
        self.assistant_avatar = f'{self.images}/stars-ai.svg'

        # Logos
        self.ai4accountancy_logo = f"{self.images}/ai4accountancy_logo.png"
