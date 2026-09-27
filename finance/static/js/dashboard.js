const transactionDialog = document.querySelector('#transaction-dialog');

if (transactionDialog) {
    document.querySelectorAll('[data-open-transaction]').forEach((trigger) => {
        trigger.addEventListener('click', (event) => {
            event.preventDefault();
            transactionDialog.showModal();
            transactionDialog.querySelector('input[name="description"]').focus();
        });
    });

    document.querySelectorAll('[data-close-dialog]').forEach((trigger) => {
        trigger.addEventListener('click', () => transactionDialog.close());
    });

    transactionDialog.addEventListener('click', (event) => {
        if (event.target === transactionDialog) {
            transactionDialog.close();
        }
    });
}

const dashboardSidebar = document.querySelector('.dashboard-sidebar');
const menuToggle = document.querySelector('[data-menu-toggle]');

if (dashboardSidebar && menuToggle) {
    menuToggle.addEventListener('click', () => {
        const isOpen = dashboardSidebar.classList.toggle('is-open');
        menuToggle.setAttribute('aria-expanded', String(isOpen));
        menuToggle.setAttribute('aria-label', isOpen ? 'Fechar navegação' : 'Abrir navegação');
    });

    dashboardSidebar.querySelectorAll('.dashboard-nav-link').forEach((link) => {
        link.addEventListener('click', () => {
            dashboardSidebar.classList.remove('is-open');
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.setAttribute('aria-label', 'Abrir navegação');
        });
    });
}