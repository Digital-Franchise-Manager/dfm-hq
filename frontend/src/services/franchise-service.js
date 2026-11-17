import { supabase } from '../utils/supabaseClient'; // Adjust path to your Supabase client

/**
 * Fetch public franchise branding profile by ID for match cards, leaderboards, etc.
 */
export async function getFranchisePublicProfile(opponentId) {
  const { data, error } = await supabase
    .from('franchise_public_profiles')
    .select('*')
    .eq('franchise_id', opponentId)
    .single();

  if (error) {
    console.error('Error fetching franchise public profile:', error.message);
    return null;
  }

  return data;
}
