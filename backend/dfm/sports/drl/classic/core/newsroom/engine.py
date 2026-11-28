"""Deterministic classic newsroom publishing; no paid LLM or shared feed."""
from typing import Protocol
from .models import NewsArticle,NewsCategory
class NewsroomRepository(Protocol):
    def append_once(self,article:NewsArticle)->bool: ...
    def list_articles(self,league_id:str,limit:int=25)->tuple[NewsArticle,...]: ...
class NewsroomEngine:
    mode="classic"
    def __init__(self,repository:NewsroomRepository):self._repository=repository
    def publish_match_report(self,*,article_id:str,league_id:str,round_number:int,fixture_completed:bool,stats_verified:bool,title:str,summary:str,match_analysis:str,motm_name:str|None,round_awards_finalised:bool)->NewsArticle:
        if not fixture_completed or not stats_verified:raise RuntimeError("match report requires a completed fixture and verified statistics")
        # Weekly award details are withheld until the whole round is finalised.
        award_line=f" Man of the Match: {motm_name}." if round_awards_finalised and motm_name else ""
        article=NewsArticle(article_id,"classic",league_id,round_number,NewsCategory.MATCH_REPORT,title,summary,match_analysis+award_line)
        if not self._repository.append_once(article):raise ValueError("article has already been published")
        return article
    def publish_round_awards(self,*,article_id:str,league_id:str,round_number:int,awards_finalised:bool,title:str,summary:str,award_report:str)->NewsArticle:
        if not awards_finalised:raise RuntimeError("weekly awards must be published together after every assigned fixture is verified")
        article=NewsArticle(article_id,"classic",league_id,round_number,NewsCategory.ROUND_AWARDS,title,summary,award_report)
        if not self._repository.append_once(article):raise ValueError("article has already been published")
        return article
    def feed(self,league_id:str,limit:int=25)->tuple[NewsArticle,...]:
        if not league_id.strip() or not 1<=limit<=100:raise ValueError("valid league and feed limit required")
        return tuple(a for a in self._repository.list_articles(league_id,limit) if a.mode=="classic")
