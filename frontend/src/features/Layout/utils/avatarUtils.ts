/**
 * Generates avatar props based on an email address
 * @param email - User's email address
 * @param size - Optional size override for the avatar
 * @returns Avatar props object with background color and initials
 */
export const getAvatarProps = (email: string, size?: { width: number; height: number }) => {
  // Get the local part of the email (before @)
  const localPart = email.split('@')[0];

  // Convert email local part to name-like format for initials
  // e.g., "john.doe" -> "John Doe"
  const nameParts = localPart
    .split(/[._-]/)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');

  return {
    sx: {
      bgcolor: 'primary.main',
      ...(size && size),
    },
    children: nameParts
      .split(' ')
      .slice(0, 2) // Take first two parts if available
      .map(part => part[0])
      .join(''),
  };
};
