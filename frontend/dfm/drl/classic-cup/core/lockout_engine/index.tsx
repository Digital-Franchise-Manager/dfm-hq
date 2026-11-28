import React from "react";

type LockoutNoticeProps = { context?: string };

export function LockoutNotice({ context = "competition actions" }: LockoutNoticeProps) {
  return <p className="drlcc-inline-note">Player lockout validation is controlled by the Classic Lockout service. {context} remain unavailable until that service is connected.</p>;
}
