"""招标信息抓取模块 + ScraperRegistry。"""


class ScraperRegistry:
    """站点 Scraper 注册中心。懒加载，避免 import 时立即初始化所有 scraper。"""
    _scrapers = None

    @classmethod
    def all(cls) -> list:
        """返回所有已注册的 scraper 实例列表。"""
        if cls._scrapers is None:
            cls._scrapers = cls._load_all()
        return cls._scrapers

    @classmethod
    def _load_all(cls) -> list:
        """实例化所有站点 scraper。延迟 import 避免循环依赖。"""
        import importlib
        import logging
        logger = logging.getLogger(__name__)

        scrapers = []
        for module_name, class_name in [
            ("ccgp", "CcgpScraper"),
            ("ggzy", "GgzyScraper"),
            ("jhygcg", "JhygcgScraper"),
            ("jhzjcs", "JhzjcsScraper"),
        ]:
            try:
                mod = importlib.import_module(f".{module_name}", package=__name__)
                scraper_cls = getattr(mod, class_name)
                scrapers.append(scraper_cls())
                logger.info(f"Loaded scraper: {module_name}")
            except Exception as e:
                logger.warning(f"Scraper {module_name} 加载失败: {e}")
        return scrapers

    @classmethod
    def reload(cls):
        """强制重新加载（测试用）。"""
        cls._scrapers = None
