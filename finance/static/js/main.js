document.documentElement.classList.add('js');

const themeToggle = document.querySelector('.theme-toggle');
const savedTheme = localStorage.getItem('finance-theme');

if (savedTheme === 'dark') {
	document.documentElement.dataset.theme = 'dark';
}

if (themeToggle) {
	const isDark = document.documentElement.dataset.theme === 'dark';
	themeToggle.setAttribute('aria-pressed', String(isDark));
	themeToggle.setAttribute('aria-label', isDark ? 'Ativar tema claro' : 'Ativar tema escuro');

	themeToggle.addEventListener('click', () => {
		const enableDark = document.documentElement.dataset.theme !== 'dark';
		document.documentElement.dataset.theme = enableDark ? 'dark' : 'light';
		themeToggle.setAttribute('aria-pressed', String(enableDark));
		themeToggle.setAttribute('aria-label', enableDark ? 'Ativar tema claro' : 'Ativar tema escuro');
		localStorage.setItem('finance-theme', enableDark ? 'dark' : 'light');
	});
}