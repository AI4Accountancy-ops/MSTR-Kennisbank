import { ReactNode } from 'react';

/**
 * Navigation menu item configuration
 */
export interface MenuItem {
  /** Text to display for the menu item */
  text: string;
  /** Icon component to display next to the text */
  icon: ReactNode;
  /** Navigation path for the menu item */
  to: string;
  /** Optional action identifier for the menu item */
  action?: string;
}

/**
 * Logo configuration for the sidebar
 */
export interface LogoConfig {
  /** URL or path to the logo image */
  src: string;
  /** Alt text for the logo image */
  alt: string;
  /** Width of the logo (CSS value) */
  width?: string | number;
  /** Height of the logo (CSS value) */
  height?: string | number;
}

/**
 * Base configuration for the sidebar
 */
interface BaseSidebarProps {
  /** Whether the sidebar is being rendered in mobile view */
  isMobile?: boolean;
  /** Navigation menu items to display */
  menuItems: MenuItem[];
  /** Submenu items to display */
  subMenuItems?: MenuItem[];
  /** Optional custom content to replace the default sidebar body */
  customContent?: ReactNode;
  /** Hide the top menu section when true */
  hideMenu?: boolean;
  /** Hide the chat history list when true */
  hideChatHistory?: boolean;
}

/**
 * Props when using logo mode
 */
interface LogoSidebarProps extends BaseSidebarProps {
  /** Logo configuration */
  logo: LogoConfig;
  /** Title should be undefined when using logo */
  title?: undefined;
}

/**
 * Props when using title mode
 */
interface TitleSidebarProps extends BaseSidebarProps {
  /** Title text to display */
  title?: string;
  /** Logo should be undefined when using title */
  logo?: undefined;
}

/**
 * Combined props type for the Sidebar component
 * Ensures either logo or title is provided, but not both
 */
export type SidebarProps = LogoSidebarProps | TitleSidebarProps;
