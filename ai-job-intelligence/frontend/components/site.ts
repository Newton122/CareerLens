import { FaGithub, FaLinkedin } from "react-icons/fa";
import type { IconType } from "react-icons";

/**
 * Site-wide links, defined once.
 *
 * The Footer and the Contact page both render these. Keeping two copies is how
 * the API base URL ended up hardcoded in three files and silently wrong in two
 * of them, so there is a single list here.
 */

export const GITHUB_URL = "https://github.com/Newton122";
export const LINKEDIN_URL =
  "https://www.linkedin.com/in/brighton-matikiti-1a48b2365";

export interface SocialLink {
  icon: IconType;
  label: string;
  href: string;
}

export const SOCIAL_LINKS: SocialLink[] = [
  { icon: FaGithub, label: "GitHub", href: GITHUB_URL },
  { icon: FaLinkedin, label: "LinkedIn", href: LINKEDIN_URL },
];

/** Props every outbound link needs: new tab, and no window.opener handle. */
export const EXTERNAL_LINK_PROPS = {
  target: "_blank",
  rel: "noopener noreferrer",
} as const;
