/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";

patch(WebClient.prototype, {
	/**
	* @override
	*/
	setup() {
		super.setup();
		// Update Favicons
		const favicon = `/web/image/res.company/${this.env.services.company.currentCompany.id}/favicon`;
		const icons = document.querySelectorAll("link[rel*='icon']");
		for (const icon of icons) {
			if (icon.rel != 'apple-touch-icon')
				icon.href = favicon
		}
	}
});
