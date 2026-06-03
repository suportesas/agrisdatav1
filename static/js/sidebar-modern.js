/**
 * Sidebar Moderno - JavaScript
 * ERP Agrícola
 */

document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  const collapseBtn = document.getElementById('collapseBtn');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const navItems = document.querySelectorAll('.nav-item.has-submenu');
  const menuToggle = document.getElementById('menuToggle'); // Botão mobile na navbar
  
  // Toggle Collapse
  if (collapseBtn) {
    collapseBtn.addEventListener('click', function() {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    });
  }

  // Restore collapsed state
  if (localStorage.getItem('sidebarCollapsed') === 'true') {
    sidebar.classList.add('collapsed');
  }

  // Posiciona o flyout do submenu verticalmente quando a sidebar está recolhida
  function positionFlyout(item) {
    if (!sidebar.classList.contains('collapsed')) return;
    const navLink = item.querySelector('.nav-link');
    const submenu = item.querySelector('.nav-submenu');
    if (!navLink || !submenu) return;

    const rect = navLink.getBoundingClientRect();
    const viewportH = window.innerHeight;
    const submenuH = Math.min(submenu.scrollHeight || 300, viewportH * 0.8);

    let top = rect.top;
    // Impede que o flyout ultrapasse a borda inferior da tela
    if (top + submenuH > viewportH - 8) {
      top = viewportH - submenuH - 8;
    }
    if (top < 8) top = 8;

    submenu.style.top = top + 'px';
    submenu.style.maxHeight = (viewportH * 0.8) + 'px';
  }

  // Toggle Submenu
  navItems.forEach(item => {
    const navLink = item.querySelector('.nav-link');

    navLink.addEventListener('click', function(e) {
      e.preventDefault();

      const isOpen = item.classList.contains('open');

      // Close other submenus
      navItems.forEach(otherItem => {
        if (otherItem !== item) {
          otherItem.classList.remove('open');
        }
      });

      // Toggle current submenu
      item.classList.toggle('open', !isOpen);

      // Posiciona o flyout se a sidebar estiver recolhida
      if (!isOpen) {
        positionFlyout(item);
      }
    });
  });

  // Fecha flyouts ao clicar fora da sidebar quando recolhida
  document.addEventListener('click', function(e) {
    if (!sidebar.classList.contains('collapsed')) return;
    if (!sidebar.contains(e.target)) {
      navItems.forEach(item => item.classList.remove('open'));
    }
  });

  // Toggle Nested Submenu (submenu dentro de submenu) - usando delegação de eventos
  document.addEventListener('click', function(e) {
    const nestedSubmenuLink = e.target.closest('.nav-submenu li.has-submenu > a');
    
    if (nestedSubmenuLink) {
      e.preventDefault();
      e.stopPropagation();
      
      const nestedItem = nestedSubmenuLink.closest('li.has-submenu');
      console.log('Nested submenu clicked:', nestedSubmenuLink.textContent.trim());
      console.log('Current open state:', nestedItem.classList.contains('open'));
      
      nestedItem.classList.toggle('open');
      
      console.log('New open state:', nestedItem.classList.contains('open'));
    }
  });

  // Submenu Search Functionality
  const searchInputs = document.querySelectorAll('.submenu-search input');
  
  searchInputs.forEach(input => {
    input.addEventListener('input', function() {
      const searchTerm = this.value.toLowerCase();
      const submenu = this.closest('.nav-submenu');
      const items = submenu.querySelectorAll('li:not(.submenu-search)');
      let visibleCount = 0;
      
      items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          item.style.display = '';
          visibleCount++;
        } else {
          item.style.display = 'none';
        }
      });
      
      // Show "no results" message if needed
      // (Optional: add a .submenu-empty element in HTML)
    });
  });

  // Mobile: Toggle sidebar with menuToggle button from navbar
  if (menuToggle) {
    menuToggle.addEventListener('click', function() {
      sidebar.classList.toggle('mobile-open');
      sidebarOverlay.classList.toggle('active');
      document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
    });
  }

  // Close sidebar when clicking overlay
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', function() {
      sidebar.classList.remove('mobile-open');
      sidebarOverlay.classList.remove('active');
      document.body.style.overflow = '';
    });
  }

  // Highlight active page
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-submenu a, .nested-submenu a, .nav-link');
  
  navLinks.forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
      
      // Open parent submenu if exists
      const parentItem = link.closest('.nav-item.has-submenu');
      if (parentItem) {
        if (!parentItem.hasAttribute('data-start-collapsed')) {
          parentItem.classList.add('open');
        }
      }
      
      // Open parent nested submenu if exists
      const nestedParentItem = link.closest('.nav-submenu li.has-submenu');
      if (nestedParentItem) {
        nestedParentItem.classList.add('open');
      }
    }
  });

  // Keyboard Navigation
  document.addEventListener('keydown', function(e) {
    // Alt + M to toggle sidebar
    if (e.altKey && e.key === 'm') {
      e.preventDefault();
      sidebar.classList.toggle('collapsed');
    }
    
    // Escape to close sidebar on mobile
    if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
      sidebar.classList.remove('mobile-open');
      sidebarOverlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
});
