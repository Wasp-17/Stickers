const byId = id => document.getElementById(id);

const sectionPresentation = [
  { name: 'КОТЫ', icon: '🐈' }, { name: 'IT', icon: '⌨' }, { name: 'КОСМОС', icon: '✦' },
  { name: 'ТУРИЗМ', icon: '⌁' }, { name: 'МУЗЫКА', icon: '♫' }, { name: 'СПОРТ', icon: '●' },
  { name: 'БИЗНЕС', icon: '↗' }, { name: 'КУЛИНАРИЯ', icon: '♨' }, { name: 'НАУКА', icon: '⚗' },
];

let catalog = null;

function renderSections() {
  const available = new Set(catalog.filters.sections);
  const grid = byId('section-grid');
  for (const section of sectionPresentation) {
    const enabled = available.has(section.name);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'section-card';
    button.dataset.section = section.name;
    button.disabled = !enabled;
    button.innerHTML = `<span class="section-icon" aria-hidden="true">${section.icon}</span><span class="section-name">${section.name}</span>${enabled ? '' : '<span class="section-note">скоро</span>'}`;
    if (enabled) button.addEventListener('click', () => { window.location.href = `catalog.html?section=${encodeURIComponent(section.name)}`; });
    grid.append(button);
  }
}

async function loadHome() {
  try {
    const response = await fetch('catalog-data/site_catalog.json');
    if (!response.ok) throw new Error('catalog data unavailable');
    catalog = await response.json();
    renderSections();
  } catch (error) {
    console.error(error);
    byId('sections-status').textContent = 'Не удалось загрузить разделы каталога. Обнови страницу.';
  }
}

const accountStorageKey = StickerStore.keys.account;
const accountSessionKey = StickerStore.keys.session;
const accountPanel = byId('account-panel');
const accountForm = byId('account-form');
let accountMode = 'register';

function safeReturnTarget() {
  const target = new URLSearchParams(window.location.search).get('return') || '';
  return /^(?:catalog|account|checkout)\.html(?:[?#]|$)/.test(target) ? target : '';
}

function readLocalAccount() {
  return StickerStore.account();
}

function accountInitial(name) {
  return (name || 'Я').trim().charAt(0).toLocaleUpperCase('ru-RU') || 'Я';
}

function setAccountStatus(message = '', success = false) {
  const status = byId('account-status');
  status.textContent = message;
  status.classList.toggle('is-success', success);
}

function setAccountMode(mode) {
  accountMode = mode;
  const registering = mode === 'register';
  const accountExists = Boolean(readLocalAccount());
  byId('registration-tab').setAttribute('aria-selected', String(registering));
  byId('login-tab').setAttribute('aria-selected', String(!registering));
  byId('account-name-field').hidden = !registering;
  byId('account-name').required = registering;
  byId('account-password').autocomplete = registering ? 'new-password' : 'current-password';
  byId('account-panel-title').textContent = registering ? 'Создать аккаунт' : 'Войти';
  byId('account-panel-copy').textContent = registering
    ? accountExists ? 'В этом браузере уже создан аккаунт. Можно войти в него.' : 'Сохраним один аккаунт в этом браузере.'
    : accountExists ? 'Введи почту и пароль своего аккаунта.' : 'Сначала создай аккаунт — это займёт меньше минуты.';
  byId('account-submit').textContent = registering ? 'Создать аккаунт' : 'Войти';
  setAccountStatus(accountExists && registering ? 'Для этой локальной версии доступен один аккаунт.' : '');
}

function openAccountPanel(mode) {
  if (localStorage.getItem(accountSessionKey) === 'active') renderAccountState();
  else setAccountMode(mode);
  accountPanel.hidden = false;
  byId('open-login').setAttribute('aria-expanded', 'true');
  byId('open-registration').setAttribute('aria-expanded', 'true');
  byId('account-button').setAttribute('aria-expanded', 'true');
  requestAnimationFrame(() => {
    const firstField = mode === 'register' ? byId('account-name') : byId('account-email');
    if (!byId('account-auth-view').hidden) firstField.focus();
  });
}

function closeAccountPanel() {
  accountPanel.hidden = true;
  for (const id of ['open-login', 'open-registration', 'account-button']) byId(id).setAttribute('aria-expanded', 'false');
  setAccountStatus();
}

function bytesToBase64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

async function passwordHash(password, salt) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations: 150000, hash: 'SHA-256' }, key, 256);
  return bytesToBase64(new Uint8Array(bits));
}

function renderAccountState() {
  const account = readLocalAccount();
  const signedIn = Boolean(account && localStorage.getItem(accountSessionKey) === 'active');
  byId('guest-account-actions').hidden = signedIn;
  byId('account-button').hidden = !signedIn;
  byId('account-auth-view').hidden = signedIn;
  byId('account-profile-view').hidden = !signedIn;
  if (!signedIn) return;
  const initial = accountInitial(account.name);
  byId('account-avatar').textContent = initial;
  byId('profile-avatar').textContent = initial;
  byId('account-button-name').textContent = account.name;
  byId('profile-name').textContent = account.name;
  byId('profile-email').textContent = account.email;
}

async function submitAccount(event) {
  event.preventDefault();
  const submit = byId('account-submit');
  const email = byId('account-email').value.trim().toLocaleLowerCase('ru-RU');
  const password = byId('account-password').value;
  const existing = readLocalAccount();
  setAccountStatus();

  if (!byId('account-email').checkValidity()) return setAccountStatus('Проверь адрес электронной почты.');
  if (password.length < 8) return setAccountStatus('Пароль должен содержать не меньше 8 символов.');

  submit.disabled = true;
  try {
    if (accountMode === 'register') {
      const name = byId('account-name').value.trim();
      if (!name) return setAccountStatus('Напиши, как к тебе обращаться.');
      if (existing) return setAccountStatus('Один аккаунт уже создан. Переключись на вкладку «Вход».');
      const salt = crypto.getRandomValues(new Uint8Array(16));
      const hash = await passwordHash(password, salt);
      localStorage.setItem(accountStorageKey, JSON.stringify({ name, email, salt: bytesToBase64(salt), hash }));
    } else {
      if (!existing) return setAccountStatus('Сначала создай аккаунт во вкладке «Регистрация».');
      const salt = Uint8Array.from(atob(existing.salt), character => character.charCodeAt(0));
      const hash = await passwordHash(password, salt);
      if (email !== existing.email || hash !== existing.hash) return setAccountStatus('Почта или пароль не подходят.');
    }
    localStorage.setItem(accountSessionKey, 'active');
    accountForm.reset();
    renderAccountState();
    const returnTarget = safeReturnTarget();
    if (returnTarget) window.location.href = returnTarget;
  } catch (error) {
    console.error(error);
    setAccountStatus('Не удалось сохранить аккаунт в этом браузере.');
  } finally {
    submit.disabled = false;
  }
}

byId('open-login').addEventListener('click', () => openAccountPanel('login'));
byId('open-registration').addEventListener('click', () => openAccountPanel('register'));
byId('account-button').addEventListener('click', () => accountPanel.hidden ? openAccountPanel('login') : closeAccountPanel());
byId('close-account-panel').addEventListener('click', closeAccountPanel);
byId('registration-tab').addEventListener('click', () => setAccountMode('register'));
byId('login-tab').addEventListener('click', () => setAccountMode('login'));
byId('toggle-password').addEventListener('click', () => {
  const password = byId('account-password');
  const showing = password.type === 'text';
  password.type = showing ? 'password' : 'text';
  byId('toggle-password').textContent = showing ? 'Показать' : 'Скрыть';
  byId('toggle-password').setAttribute('aria-label', showing ? 'Показать пароль' : 'Скрыть пароль');
});
accountForm.addEventListener('submit', submitAccount);
byId('logout-button').addEventListener('click', () => {
  localStorage.removeItem(accountSessionKey);
  closeAccountPanel();
  renderAccountState();
});
document.addEventListener('pointerdown', event => {
  if (!accountPanel.hidden && !event.target.closest('.account-area')) closeAccountPanel();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !accountPanel.hidden) closeAccountPanel();
});

setAccountMode(readLocalAccount() ? 'login' : 'register');
renderAccountState();
const requestedAccountMode = new URLSearchParams(window.location.search).get('account');
if (!StickerStore.signedIn() && ['login', 'register'].includes(requestedAccountMode)) openAccountPanel(requestedAccountMode);

loadHome();
