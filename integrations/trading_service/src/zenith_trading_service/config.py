"""Operator-only private configuration; native files and original defaults stay intact."""
from dataclasses import dataclass
from pathlib import Path
import subprocess
from zenith_integrations.config import private_origin
from . import PIN


@dataclass(frozen=True)
class TradingConfig:
    source_root: str
    state_directory: str
    inference_origin: str
    inference_key_file: str
    deadline_seconds: int=900
    max_output_tokens: int=256

    def __post_init__(self):
        private_origin(self.inference_origin)
        if type(self.deadline_seconds) is not int or not 1<=self.deadline_seconds<=900:
            raise ValueError('Use a bounded native worker deadline')
        if type(self.max_output_tokens) is not int or not 32<=self.max_output_tokens<=2048:
            raise ValueError('Use a bounded output budget supported by the inference endpoint')
        source=Path(self.source_root).resolve()
        state=Path(self.state_directory).expanduser().resolve()
        if state==source or source in state.parents:
            raise ValueError('Native source is immutable; select separate private state')

    def verify_source(self):
        root=Path(self.source_root).resolve()
        def git(*args):
            return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.DEVNULL,timeout=15).strip()
        if git('rev-parse','HEAD')!=PIN or git('status','--porcelain','--untracked-files=all'):
            raise ValueError('Use the exact unchanged audited native checkout')
        if not (root/'tradingagents/graph/trading_graph.py').is_file():
            raise ValueError('Pinned native graph is missing')
        return root

    def native_config(self,root,account_root,run_root,defaults):
        # Explicit settings take precedence over native environment defaults.
        config=dict(defaults)
        config.update(llm_provider='openai_compatible',deep_think_provider='openai_compatible',
            quick_think_provider='openai_compatible',quick_think_llm='zenith',deep_think_llm='zenith',
            backend_url=self.inference_origin.rstrip('/')+'/v1',
            quick_think_backend_url=self.inference_origin.rstrip('/')+'/v1',
            deep_think_backend_url=self.inference_origin.rstrip('/')+'/v1',
            results_dir=str(run_root/'reports'),data_cache_dir=str(account_root/'cache'),
            memory_log_path=str(account_root/'memory/trading_memory.md'),
            checkpoint_enabled=True,max_debate_rounds=1,max_risk_discuss_rounds=1,
            max_tool_rounds=2,max_recur_limit=100,max_tokens=self.max_output_tokens,
            temperature=0.0,llm_max_retries=3,
            # Fixed native read-only data vendors, never a model-selected URL.
            data_vendors={'core_stock_apis':'yfinance','technical_indicators':'yfinance',
                'fundamental_data':'sec_edgar,yfinance','news_data':'yfinance',
                'macro_data':'fred','prediction_markets':'polymarket'},tool_vendors={})
        return config
