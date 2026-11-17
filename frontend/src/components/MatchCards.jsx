import React, { useEffect, useState } from 'react';
import { getFranchisePublicProfile } from '../services/franchiseService';

export default function MatchCard({ match }) {
  const [opponent, setOpponent] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadOpponentData() {
      if (!match?.opponentId) return;
      
      // HERE IS WHERE YOU CALL IT:
      const opponentData = await getFranchisePublicProfile(match.opponentId);
      
      setOpponent(opponentData);
      setLoading(false);
    }

    loadOpponentData();
  }, [match]);

  if (loading) return <div>Loading opponent...</div>;
  if (!opponent) return <div>Opponent not found</div>;

  return (
    <div className="match-card" style={{ borderColor: opponent.primary_colour }}>
      <img src={opponent.primary_logo_url} alt={opponent.secondary_name} width="40" />
      <h3>{opponent.primary_name} {opponent.secondary_name}</h3>
      <span className="badge">{opponent.abbreviated_name}</span>
    </div>
  );
}
