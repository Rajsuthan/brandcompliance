import React from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';

const UserProfile: React.FC = () => {
  const { user, signOut } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <div className="flex items-center gap-4">
      {user.photoURL && (
        <img 
          src={user.photoURL} 
          alt="Profile" 
          className="w-8 h-8 rounded-full"
        />
      )}
      <div className="flex flex-col">
        <span className="text-sm font-medium">{user.displayName || user.email}</span>
        <Button 
          variant="link" 
          size="sm" 
          className="text-xs text-zinc-400 p-0 h-auto" 
          onClick={signOut}
        >
          Sign out
        </Button>
      </div>
    </div>
  );
};

export default UserProfile;
