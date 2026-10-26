"""Keep native decision/risk evidence; never fabricate calibrated confidence."""
from . import PIN
from zenith_integrations.shared.redaction import redact

RATINGS=frozenset({'Buy','Overweight','Hold','Underweight','Sell'})
REPORTS=('market_report','sentiment_report','news_report','fundamentals_report')


def analysis_report(state,signal,ticker,as_of,secret=''):
    if not isinstance(state,dict):
        raise ValueError('Native graph did not return a state')
    missing=[]
    for key in (*REPORTS,'investment_plan','trader_investment_plan','final_trade_decision'):
        if not isinstance(state.get(key),str) or not state[key].strip():
            missing.append(key)
    for section,keys in [('investment_debate_state',('bull_history','bear_history')),
                          ('risk_debate_state',('aggressive_history','conservative_history','neutral_history'))]:
        values=state.get(section)
        if not isinstance(values,dict) or any(not isinstance(values.get(key),str) or not values[key].strip() for key in keys):
            missing.append(section)
    complete=not missing and signal in RATINGS
    return redact({'native_source_pin':PIN,'ticker':ticker,'as_of':as_of,'operation':'research',
        'model':'zenith','provider':'openai_compatible','all_native_roles_completed':not missing,
        'workflow_status':'completed' if complete else 'requires_review',
        'rating':signal if complete else 'REVIEW','native_rating':signal,
        'missing_evidence':missing,'confidence':None,'confidence_note':'No calibrated probability supplied by the native graph',
        'analysts':{key:state.get(key) for key in REPORTS},
        'research_debate':state.get('investment_debate_state'),'research_plan':state.get('investment_plan'),
        'trader_plan':state.get('trader_investment_plan'),'risk_debate':state.get('risk_debate_state'),
        'portfolio_decision':state.get('final_trade_decision'),
        'live_orders_enabled':False,'financial_advice':False,
        'point_in_time':{'native_date_guards_preserved':True,'all_feed_availability_verified':False,
                         'model_training_knowledge_cutoff_verified':False}},(secret,))
