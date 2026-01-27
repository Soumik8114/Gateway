(() => {
	function setActiveNavLink(clickedLink) {
		const nav = clickedLink.closest(".nav");
		if (!nav) return;

		nav.querySelectorAll(".nav__link").forEach((link) => {
			link.classList.remove("nav__link--active");
			link.removeAttribute("aria-current");
		});

		clickedLink.classList.add("nav__link--active");
		clickedLink.setAttribute("aria-current", "page");
	}

	document.addEventListener("click", (event) => {
		const link = event.target instanceof Element ? event.target.closest(".nav__link") : null;
		if (!link) return;
		setActiveNavLink(link);
	});

	// Optional helper (not currently wired to UI):
	// window.setTheme("dark"|"light") will toggle the root class.
	window.setTheme = (theme) => {
		const isDark = theme === "dark";
		document.documentElement.classList.toggle("dark", isDark);
	};
})();
