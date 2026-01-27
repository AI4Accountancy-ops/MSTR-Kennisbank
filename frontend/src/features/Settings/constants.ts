export const SETTINGS_SECTIONS = [
  'account-team',
  'plan-billing',
  'security',
  'usage-quotas',
  'integrations',
  'support',
  'legal',
] as const;

export type SettingsSection = (typeof SETTINGS_SECTIONS)[number];

export const DEFAULT_SETTINGS_SECTION: SettingsSection = 'account-team';

export const LAST_SECTION_KEY = 'settings:lastSection';

export function isValidSettingsSection(value: string | null | undefined): value is SettingsSection {
  if (typeof value !== 'string') return false;
  return SETTINGS_SECTIONS.includes(value as SettingsSection);
}
