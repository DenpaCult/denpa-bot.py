from dataclasses import dataclass, field


@dataclass
class EditRule:
    """ping these roles when a message is edited at least threshold_s seconds after it was posted"""

    threshold_s: int
    role_ids: list[int] = field(default_factory=list)


@dataclass
class EditCfg:
    """
    Settings for old message edit reporting
    """

    guild_id: int
    enabled: bool
    report_channel_id: int | None
    rules: list[EditRule] = field(default_factory=list)
    exempt_role_ids: set[int] = field(default_factory=set)

    def rule_for(self, age_s: float) -> EditRule | None:
        """the rule with the largest threshold that a message of this age has passed, if any"""
        passed = [rule for rule in self.rules if age_s >= rule.threshold_s]


        # FIXME(kajo): is this lint superfluous?
        return max(passed, key=lambda rule: rule.threshold_s, default=None)  # ty: ignore[unresolved-attribute]
