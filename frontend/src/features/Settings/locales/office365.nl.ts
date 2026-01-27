export interface Office365Strings {
  readonly integration: {
    readonly title: string;
    readonly subtitle: string;
    readonly status: { readonly connected: string; readonly disconnected: string };
    readonly expectations: { readonly title: string; readonly description: string };
    readonly scopes: { readonly outlook: { readonly title: string; readonly description: string } };
    readonly consentNote: string;
    readonly docsLinkText: string;
    readonly connect: string;
    readonly connectNote: string;
    readonly connectedAsTitle: string;
    readonly connectedAsNote: string;
    readonly buttons: {
      readonly testAccess: string;
      readonly testing: string;
      readonly disconnect: string;
    };
    readonly dialogTitle: string;
    readonly steps: ReadonlyArray<{ readonly title: string; readonly description: string }>;
  };
  readonly inbox: {
    readonly headerTitle: string;
    readonly headerSummary: string;
    readonly customers: string;
  };
  readonly notification: {
    readonly new: string;
    readonly title: string;
    readonly description: string;
    readonly setup: string;
    readonly hide: string;
    readonly tooltip: string;
  };
}

export const office365StringsNl: Office365Strings = {
  integration: {
    title: 'Microsoft 365',
    subtitle: 'Koppel uw Office 365 services aan Belasting AI',
    status: { connected: 'Verbonden', disconnected: 'Niet verbonden' },
    expectations: {
      title: 'Wat kan je verwachten?',
      description:
        'Belasting AI zal verbinden via je Microsoft account. Je logt in, verleent beperkte rechten, en we ronden de koppeling af. Je kan dit later altijd intrekken.',
    },
    scopes: {
      outlook: {
        title: 'Outlook e-mail',
        description: 'Belasting AI kan je email lezen, labelen en concept berichten klaarzetten.',
      },
    },
    consentNote:
      'Door te verbinden gaat u akkoord met het delen van beperkte Microsoft 365-gegevens zoals hierboven omschreven. Lees meer over rechten bij Microsoft ',
    docsLinkText: 'documentatie',
    connect: 'Verbind met Microsoft 365',
    connectNote:
      'U wordt doorgestuurd naar Microsoft om in te loggen en rechten te verlenen. We slaan uw wachtwoord nooit op.',
    connectedAsTitle: 'Verbonden als',
    connectedAsNote:
      'Microsoft 365 is actief gekoppeld. U kunt de toegang op elk moment intrekken.',
    buttons: { testAccess: 'Test toegang', testing: 'Testen…', disconnect: 'Verbinding verbreken' },
    dialogTitle: 'Microsoft 365 verbinden',
    steps: [
      {
        title: 'Microsoft-account verifiëren',
        description: 'We leiden u door naar Microsoft om in te loggen.',
      },
      {
        title: 'Toestemmingen verlenen',
        description: 'Geef AI4Accountancy toegang tot specifieke Office 365-onderdelen.',
      },
      {
        title: 'Koppeling voltooien',
        description: 'We ronden de configuratie af en valideren de toegang.',
      },
    ],
  },
  inbox: {
    headerTitle: 'Support',
    headerSummary: '',
    customers: 'Klanten',
  },
  notification: {
    new: 'Nieuw',
    title: 'Outlook integratie',
    description: 'Verbind met Outlook - Office 365 voor je eigen Email-Agent.',
    setup: 'Instellen',
    hide: 'Verbergen',
    tooltip: 'Activeer de koppeling met uw Microsoft 365-omgeving via Instellingen → Integraties.',
  },
};
