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

  // Toggle Submenu
  navItems.forEach(item => {
    const navLink = item.querySelector('.nav-link');
    
    navLink.addEventListener('click', function(e) {
      e.preventDefault();
      
      // Close other submenus
      navItems.forEach(otherItem => {
        if (otherItem !== item) {
          otherItem.classList.remove('open');
        }
      });
      
      // Toggle current submenu
      item.classList.toggle('open');
    });
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
        parentItem.classList.add('open');
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
