(function () {
  const Calculator = window.Calculator;
  const resultEl = document.getElementById('result');
  const expressionEl = document.getElementById('expression');
  const SYMBOLS = { '+': '+', '-': '−', '*': '×', '/': '÷' };

  let state = Calculator.initialState();

  function render() {
    resultEl.textContent = state.current;
    resultEl.classList.toggle('long', state.current.length > 9);
    expressionEl.textContent = state.operator ? `${state.previous} ${SYMBOLS[state.operator]}` : '';
  }

  function dispatch(action) {
    state = Calculator.reduce(state, action);
    render();
  }

  document.querySelector('.keys').addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    const { digit, op, action } = button.dataset;
    if (digit !== undefined) dispatch({ type: 'digit', value: digit });
    else if (op) dispatch({ type: 'operator', value: op });
    else dispatch({ type: action });
  });

  const keyActions = {
    Enter: { type: 'equals' },
    '=': { type: 'equals' },
    Backspace: { type: 'backspace' },
    Escape: { type: 'clear' },
    Delete: { type: 'clear' },
    '.': { type: 'decimal' },
    ',': { type: 'decimal' },
    '%': { type: 'percent' },
  };

  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;

    let action = null;
    if (/^[0-9]$/.test(event.key)) action = { type: 'digit', value: event.key };
    else if (['+', '-', '*', '/'].includes(event.key)) action = { type: 'operator', value: event.key };
    else action = keyActions[event.key] || null;

    if (!action) return;
    event.preventDefault();
    dispatch(action);
  });

  render();
})();
