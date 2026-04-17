from __future__ import annotations

from dataclasses import dataclass

from vioscope.agents.scout import ScoutAgent, build_scout
from vioscope.agents.skeptic import SkepticAgent, build_skeptic
from vioscope.agents.spark import SparkAgent, build_spark
from vioscope.agents.synth import SynthAgent, build_synth
from vioscope.config import VioScopeConfig


@dataclass
class AgentBundle:
    scout: ScoutAgent
    skeptic: SkepticAgent
    spark: SparkAgent
    synth: SynthAgent


def build_agents(config: VioScopeConfig) -> AgentBundle:
    return AgentBundle(
        scout=build_scout(config),
        skeptic=build_skeptic(config),
        spark=build_spark(config),
        synth=build_synth(config),
    )


__all__ = ["AgentBundle", "build_agents"]
