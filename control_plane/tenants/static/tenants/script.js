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

	function togglePasswordVisibility(toggleButton) {
		const group = toggleButton.closest(".input-wrap") ?? toggleButton.parentElement;
		if (!group) return;
		const input = group.querySelector("input[type='password'], input[type='text']");
		if (!(input instanceof HTMLInputElement)) return;

		const show = input.type === "password";
		input.type = show ? "text" : "password";
		toggleButton.setAttribute("aria-pressed", show ? "true" : "false");
		toggleButton.setAttribute("aria-label", show ? "Hide password" : "Show password");
		toggleButton.title = show ? "Hide password" : "Show password";

		const icon = toggleButton.querySelector(".material-symbols-outlined");
		if (icon) icon.textContent = show ? "visibility_off" : "visibility";
	}

	document.addEventListener("click", (event) => {
		const target = event.target instanceof Element ? event.target : null;
		if (!target) return;
		const toggleButton = target.closest("[data-password-toggle]");
		if (!(toggleButton instanceof HTMLButtonElement)) return;
		togglePasswordVisibility(toggleButton);
	});
})();
