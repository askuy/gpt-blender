const toggle = document.getElementById('languageToggle');
const storageKey = 'gpt-blender-language';

function setLanguage(language) {
  const isChinese = language === 'zh';
  document.body.dataset.lang = isChinese ? 'zh' : 'en';
  document.documentElement.lang = isChinese ? 'zh-CN' : 'en';
  toggle.dataset.current = isChinese ? 'zh' : 'en';
  toggle.setAttribute('aria-label', isChinese ? '切换为英文' : 'Switch to Chinese');
  document.title = isChinese
    ? 'gpt-blender — 把想法，做成可以转动的东西。'
    : 'gpt-blender — Ideas become things you can turn.';
  try {
    localStorage.setItem(storageKey, isChinese ? 'zh' : 'en');
  } catch {
    // Private browsing can disable storage; the current page still switches.
  }
}

let initialLanguage = 'en';
try {
  initialLanguage = localStorage.getItem(storageKey) === 'zh' ? 'zh' : 'en';
} catch {
  // Keep English as the first-visit default when storage is unavailable.
}

setLanguage(initialLanguage);
toggle.addEventListener('click', () => setLanguage(document.body.dataset.lang === 'zh' ? 'en' : 'zh'));
