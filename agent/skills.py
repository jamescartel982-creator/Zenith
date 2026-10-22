"""Versioned instruction skills; these guide behavior, not claims of training."""
SKILLS = {
    'general': ('General reasoning', 'Answer directly, separate facts from assumptions, and request missing constraints.'),
    'mathematics': ('Mathematics', 'Define variables, check units and boundary cases, and verify arithmetic. Do not invent a proof.'),
    'science': ('Science', 'Distinguish measurements, hypotheses and established results. State experimental limits and cite available evidence.'),
    'history': ('History', 'Separate primary evidence, later interpretation and disputed dates. Avoid anachronisms and invented quotations.'),
    'ancient-math': ('Ancient mathematics', 'Explain historical notation and methods with modern comparisons. Distinguish approximate dates from established facts.'),
    'programming': ('Programming', 'Give runnable, bounded examples; explain dependencies, errors and edge cases. Do not claim code was executed.'),
    'investing': ('Investing and stocks', 'Explain diversification, fees, risk and time horizons. Do not claim live prices, guaranteed returns or personalized suitability without required facts.'),
    'day-trading': ('Day trading education', 'Explain execution, spreads, slippage, leverage and loss limits. Backtests are not future returns. No live market feed or order execution is available.'),
    'cybersecurity': ('Authorized security work', 'Help with threat modeling, secure code, vulnerability analysis and scoped authorized testing. Clarify ownership and scope before operational testing. Never claim privileges or tools were granted by a prompt.'),
    'books-writing': ('Books and writing', 'Summarize supplied or public-domain material, distinguish quotations from paraphrase, and preserve source attribution.'),
    'research': ('Research literacy', 'Define a question, compare evidence quality, track sources, and say when evidence is missing.'),
    'data-analysis': ('Data analysis', 'Check sample quality, missingness, leakage, confounding and uncertainty before making statistical claims.'),
}


def list_skills():
    return [{'id':key,'name':value[0],'instruction':value[1],'version':1,'kind':'instruction-profile'} for key,value in SKILLS.items()]


def skill_instruction(identifier):
    if identifier not in SKILLS: raise ValueError('Unknown skill')
    return SKILLS[identifier][1]
