"""网站配置管理服务（徐挚凌）。

字段名与《docs/接口约定.md》第 4 节一致，存储采用内存态（单进程），
测试使用符合接口的样例；不新增数据库或后端框架。
"""
from dataclasses import asdict, dataclass
from typing import Mapping

CRAWL_STRATEGIES = ("bfs", "dfs")
FREQUENCIES = ("once", "daily", "twice_daily")

DEFAULT_SITE_ID = "boss_zhipin"
DEFAULT_SITE_NAME = "BOSS直聘"


@dataclass(frozen=True, slots=True)
class SiteConfig:
    """网站采集配置，字段与《接口约定》第 4 节一致。"""

    site_id: str
    site_name: str
    base_url: str = ""
    enabled: bool = True
    keywords: tuple[str, ...] = ()
    cities: tuple[str, ...] = ()
    crawl_strategy: str = "bfs"
    start_at: str = ""
    frequency: str = "once"
    max_depth: int = 1

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "SiteConfig":
        raw = dict(values)
        site_id = str(raw.get("site_id", "") or "").strip()
        if not site_id:
            raise ValueError("site_id 不能为空")
        site_name = str(raw.get("site_name", "") or "").strip()
        if not site_name:
            raise ValueError("site_name 不能为空")
        base_url = str(raw.get("base_url", "") or "").strip()
        if not base_url:
            raise ValueError("base_url 不能为空")
        config = cls(
            site_id=site_id,
            site_name=site_name,
            base_url=base_url,
            enabled=_as_bool(raw.get("enabled"), default=True),
            keywords=_as_string_tuple(raw.get("keywords")),
            cities=_as_string_tuple(raw.get("cities")),
            crawl_strategy=str(raw.get("crawl_strategy", "bfs") or "bfs").strip().lower(),
            start_at=str(raw.get("start_at", "") or ""),
            frequency=str(raw.get("frequency", "once") or "once").strip().lower(),
            max_depth=_as_int(raw.get("max_depth"), default=1),
        )
        _validate(config)
        return config

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _as_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _as_int(value: object, default: int) -> int:
    if value in (None, ""):
        return default
    return int(value)


def _as_string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
    else:
        items = [str(item).strip() for item in value if str(item).strip()]
    return tuple(items)


def _validate(config: SiteConfig) -> None:
    if config.crawl_strategy not in CRAWL_STRATEGIES:
        raise ValueError(f"crawl_strategy 只能是 {'/'.join(CRAWL_STRATEGIES)}，实际为: {config.crawl_strategy!r}")
    if config.frequency not in FREQUENCIES:
        raise ValueError(f"frequency 只能是 {'/'.join(FREQUENCIES)}，实际为: {config.frequency!r}")
    if config.max_depth < 0:
        raise ValueError("max_depth 不能为负数")


_SITES: dict[str, SiteConfig] = {}


def reset_sites() -> None:
    """清空全部网站配置（测试用）。"""
    _SITES.clear()


def list_sites() -> list[SiteConfig]:
    return list(_SITES.values())


def get_site(site_id: str) -> SiteConfig:
    if site_id not in _SITES:
        raise KeyError(f"网站不存在: {site_id}")
    return _SITES[site_id]


def add_site(values: Mapping[str, object]) -> SiteConfig:
    config = SiteConfig.from_mapping(values)
    if config.site_id in _SITES:
        raise ValueError(f"网站已存在: {config.site_id}")
    _SITES[config.site_id] = config
    return config


def update_site(site_id: str, changes: Mapping[str, object]) -> SiteConfig:
    if site_id not in _SITES:
        raise KeyError(f"网站不存在: {site_id}")
    merged = {**_SITES[site_id].to_dict(), **dict(changes), "site_id": site_id}
    config = SiteConfig.from_mapping(merged)
    _SITES[site_id] = config
    return config


def set_site_enabled(site_id: str, enabled: bool) -> SiteConfig:
    return update_site(site_id, {"enabled": enabled})


def remove_site(site_id: str) -> SiteConfig:
    if site_id not in _SITES:
        raise KeyError(f"网站不存在: {site_id}")
    return _SITES.pop(site_id)


def ensure_default_site() -> SiteConfig:
    """按接口约定首期配置补齐 BOSS 直聘默认站点。"""
    if DEFAULT_SITE_ID not in _SITES:
        _SITES[DEFAULT_SITE_ID] = SiteConfig(
            site_id=DEFAULT_SITE_ID,
            site_name=DEFAULT_SITE_NAME,
            base_url="https://www.zhipin.com",
        )
    return _SITES[DEFAULT_SITE_ID]
