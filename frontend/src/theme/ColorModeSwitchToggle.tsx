import { Switch } from '~/components/ui/switch';
import { useTheme } from '~/components/theme-provider';

export default function ColorModeSwitchToggle() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <Switch
      variant="mui"
      checked={isDark}
      onCheckedChange={checked => setTheme(checked ? 'dark' : 'light')}
      aria-label="Thema wisselen"
    />
  );
}
