import { Button } from '~/components/ui/button';

export interface MenuButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  showBadge?: boolean;
}

export default function MenuButton({ showBadge = false, ...props }: MenuButtonProps) {
  return (
    <div className="relative inline-flex">
      {showBadge && (
        <span className="absolute right-[2px] top-[2px] inline-block size-2 rounded-full bg-destructive" />
      )}
      <Button size="icon" variant="ghost" {...props} />
    </div>
  );
}
