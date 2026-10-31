(function (root) {
  const MAX_DIGITS = 12;

  function initialState() {
    return { current: '0', previous: null, operator: null, overwrite: false, error: false };
  }

  function format(n) {
    if (!Number.isFinite(n)) return 'Error';
    return String(parseFloat(n.toPrecision(MAX_DIGITS)));
  }

  function compute(a, operator, b) {
    switch (operator) {
      case '+': return a + b;
      case '-': return a - b;
      case '*': return a * b;
      case '/': return b === 0 ? NaN : a / b;
    }
    return b;
  }

  function errorState() {
    return { ...initialState(), current: 'Error', error: true };
  }

  function inputDigit(s, digit) {
    if (s.error) s = initialState();
    if (s.overwrite) return { ...s, current: digit, overwrite: false };
    if (s.current.replace(/\D/g, '').length >= MAX_DIGITS) return s;
    if (/^-?0$/.test(s.current)) return { ...s, current: s.current.replace('0', digit) };
    return { ...s, current: s.current + digit };
  }

  function inputDecimal(s) {
    if (s.error) s = initialState();
    if (s.overwrite) return { ...s, current: '0.', overwrite: false };
    if (s.current.includes('.')) return s;
    return { ...s, current: s.current + '.' };
  }

  function evaluate(s) {
    if (s.error || s.operator === null) return s;
    const result = compute(parseFloat(s.previous), s.operator, parseFloat(s.current));
    if (!Number.isFinite(result)) return errorState();
    return { ...initialState(), current: format(result), overwrite: true };
  }

  function setOperator(s, operator) {
    if (s.error) return s;
    if (s.operator !== null && !s.overwrite) {
      const chained = evaluate(s);
      if (chained.error) return chained;
      return { ...chained, previous: chained.current, operator, overwrite: true };
    }
    return { ...s, previous: s.current, operator, overwrite: true };
  }

  function toggleSign(s) {
    if (s.error) return s;
    const current = s.current.startsWith('-') ? s.current.slice(1) : '-' + s.current;
    return { ...s, current };
  }

  function percent(s) {
    if (s.error) return s;
    return { ...s, current: format(parseFloat(s.current) / 100), overwrite: true };
  }

  function backspace(s) {
    if (s.error || s.overwrite) return s;
    const current = s.current.slice(0, -1);
    return { ...s, current: current === '' || current === '-' ? '0' : current };
  }

  function reduce(s, action) {
    switch (action.type) {
      case 'digit': return inputDigit(s, action.value);
      case 'decimal': return inputDecimal(s);
      case 'operator': return setOperator(s, action.value);
      case 'equals': return evaluate(s);
      case 'clear': return initialState();
      case 'sign': return toggleSign(s);
      case 'percent': return percent(s);
      case 'backspace': return backspace(s);
    }
    return s;
  }

  const api = { initialState, format, reduce };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  } else {
    root.Calculator = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);
