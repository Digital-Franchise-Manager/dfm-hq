"""DRAFT odds calculations; no shared engine imports or cross-mode data."""
from __future__ import annotations
import hashlib,json,math
from collections.abc import Mapping
from .models import MarketType,MarketSource,MarketOutcome,MarketCalculation,PriceMovement
MODEL_VERSION="draft-odds-1.0.0"
ALLOWED={MarketType.HEAD_TO_HEAD,MarketType.PREMIERSHIP,MarketType.FINALS_QUALIFICATION,MarketType.GRAND_FINAL_QUALIFICATION,MarketType.PLAY_OF_THE_WEEK,MarketType.MAN_OF_THE_MATCH,MarketType.MAN_OF_THE_ROUND,MarketType.PLAYER_OF_THE_YEAR,MarketType.COACH_OF_THE_YEAR,MarketType.TEAM_OF_THE_WEEK,MarketType.TEAM_OF_THE_YEAR}
def _softmax(values:Mapping[str,float],temperature:float)->dict[str,float]:
    if len(values)<2 or not math.isfinite(temperature) or temperature<=0:raise ValueError("two selections and positive finite temperature required")
    if any(not k.strip() or not math.isfinite(v) for k,v in values.items()):raise ValueError("selection IDs and projections must be valid and finite")
    scaled={k:v/temperature for k,v in values.items()};peak=max(scaled.values());exps={k:math.exp(v-peak) for k,v in scaled.items()};total=math.fsum(exps.values())
    floor=1e-12;bounded={k:max(floor,v/total) for k,v in exps.items()};norm=math.fsum(bounded.values())
    return {k:v/norm for k,v in bounded.items()}
def _price(p:float)->float:
    if not math.isfinite(p) or not 0<p<1:raise ValueError("probability must be finite and between zero and one")
    return round(1/p,4)
class OddsEngine:
    mode="draft"
    model_version=MODEL_VERSION
    def _build(self,kind:MarketType,market_id:str,probs:Mapping[str,float],labels:Mapping[str,str],source:MarketSource)->MarketCalculation:
        if kind not in ALLOWED:raise ValueError("market type is not available in this competition mode")
        if set(probs)!=set(labels) or len(probs)<2:raise ValueError("market selections and labels must match and contain at least two entries")
        outcomes=tuple(MarketOutcome(k,labels[k],p,_price(p)) for k,p in probs.items())
        return MarketCalculation(self.mode,kind,market_id,outcomes,source,self.model_version,source.verified)
    def calculate_head_to_head(self,*,market_id:str,home_id:str,home_name:str,home_projection:float,away_id:str,away_name:str,away_projection:float,source:MarketSource,margin_scale:float=35.0)->MarketCalculation:
        if home_id==away_id or not all(math.isfinite(v) and v>=0 for v in (home_projection,away_projection)):raise ValueError("distinct franchises and finite non-negative projections required")
        if not math.isfinite(margin_scale) or margin_scale<=0:raise ValueError("margin scale must be positive and finite")
        z=(home_projection-away_projection)/margin_scale;p=1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z));p=min(1-1e-12,max(1e-12,p))
        return self._build(MarketType.HEAD_TO_HEAD,market_id,{home_id:p,away_id:1-p},{home_id:home_name,away_id:away_name},source)
    def calculate_ranked_market(self,*,market_type:MarketType,market_id:str,projections:Mapping[str,float],labels:Mapping[str,str],source:MarketSource,temperature:float=1.0)->MarketCalculation:
        if market_type in (MarketType.FINALS_QUALIFICATION,MarketType.GRAND_FINAL_QUALIFICATION):raise ValueError("use calculate_qualification for separate yes/no qualification markets")
        return self._build(market_type,market_id,_softmax(projections,temperature),labels,source)
    def calculate_qualification(self,*,market_type:MarketType,market_id:str,franchise_id:str,franchise_name:str,probability:float,source:MarketSource)->MarketCalculation:
        if market_type not in (MarketType.FINALS_QUALIFICATION,MarketType.GRAND_FINAL_QUALIFICATION):raise ValueError("qualification market type required")
        if not math.isfinite(probability) or not 0<probability<1:raise ValueError("qualification probability must be between zero and one")
        yes,no=franchise_id+":yes",franchise_id+":no"
        return self._build(market_type,market_id,{yes:probability,no:1-probability},{yes:franchise_name+" qualifies",no:franchise_name+" does not qualify"},source)
    @staticmethod
    def create_price_movements(previous:MarketCalculation,revised:MarketCalculation,revision:int)->tuple[PriceMovement,...]:
        if previous.mode!="draft" or revised.mode!="draft" or previous.mode!=revised.mode or previous.market_type!=revised.market_type or previous.market_id!=revised.market_id:raise ValueError("price history cannot cross mode or market boundaries")
        if not previous.official or not revised.official or revision<2:raise ValueError("only verified revisions with revision >= 2 can be recorded")
        old={o.selection_id:o for o in previous.outcomes};new={o.selection_id:o for o in revised.outcomes}
        if old.keys()!=new.keys():raise ValueError("market selections cannot change during a revision")
        out=[]
        for key in sorted(old):
            if old[key].probability==new[key].probability and old[key].decimal_price==new[key].decimal_price:continue
            raw=json.dumps(["draft",revised.market_id,key,revision,revised.source.source_id,revised.model_version],separators=(",",":"));idem=hashlib.sha256(raw.encode()).hexdigest()
            out.append(PriceMovement(revised.market_id,key,revision,old[key].probability,new[key].probability,old[key].decimal_price,new[key].decimal_price,revised.source.source_id,revised.model_version,idem))
        return tuple(out)
