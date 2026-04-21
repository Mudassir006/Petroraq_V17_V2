/**@odoo-module**/

import { SearchPanel } from "@web/search/search_panel/search_panel";
import { patch } from "@web/core/utils/patch";


patch(SearchPanel.prototype, {
    /**
    * Handles the scroll on the SearchPanel
    * When scrolling, change top position o_resize to scroll_top
    *
    * @private
    * @param {MouseEvent} ev
    */
    _onScroll(ev) {
        if (!this.o_resize) {
            this.o_resize = document.querySelector('.o_resize');
        }
        if (this.o_resize) {
            this.o_resize.style.top = `${ev.target.scrollTop}px`;
        }
    },
    /**
    * Handles the resize feature on the SearchPanel
    *
    * @private
    * @param {MouseEvent} ev
    */
    _onStartResize(ev) {
        this.resizing = true;
        const container = this.root.el;
        container.style.width = `${Math.floor(container.getBoundingClientRect().width)}px`;
        const initialX = ev.clientX;
        const initialWidth = container.getBoundingClientRect().width;
        const resizeStoppingEvents = ["keydown", "mousedown", "mouseup"];

        // fix the width so that if the resize overflows, it doesn't affect the layout of the parent
        if (!this.root.el.style.width) {
            this.root.el.style.width = `${Math.floor(
                this.root.el.getBoundingClientRect().width
            )}px`;
        }

        // Mousemove event : resize header
        const resizeHeader = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const delta = ev.clientX - initialX;
            const newWidth = Math.max(10, initialWidth + delta);
            container.style.width = `${Math.floor(newWidth)}px`;
            container.style.maxWidth = `${Math.floor(newWidth)}px`;
        };
        window.addEventListener("mousemove", resizeHeader);

        // Mouse or keyboard events : stop resize
        const stopResize = (ev) => {
            this.resizing = false;
            // Ignores the 'left mouse button down' event as it used to start resizing
            if (ev.type === "mousedown" && ev.which === 1) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            window.removeEventListener("mousemove", resizeHeader);
            for (const eventType of resizeStoppingEvents) {
                window.removeEventListener(eventType, stopResize);
            }

            // we remove the focus to make sure that the there is no focus inside
            // the tr.  If that is the case, there is some css to darken the whole
            // thead, and it looks quite weird with the small css hover effect.
            document.activeElement.blur();
        };
        // We have to listen to several events to properly stop the resizing function. Those are:
        // - mousedown (e.g. pressing right click)
        // - mouseup : logical flow of the resizing feature (drag & drop)
        // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
        for (const eventType of resizeStoppingEvents) {
            window.addEventListener(eventType, stopResize);
        }
    }
})
