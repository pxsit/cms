/* Contest Management System - http://cms-dev.github.io/
 * Copyright © 2026 Pasit Sangprachathanarak <ouipingpasit@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/* jqPlot 1.0.9 (2016) still calls a few jQuery utility functions that
 * jQuery 4 removed. Put them back for jqPlot's sake; nothing else in CMS
 * should use them. */
(function ($) {
    "use strict";

    if (!$.isArray) {
        $.isArray = Array.isArray;
    }
    if (!$.isFunction) {
        $.isFunction = function (obj) {
            return typeof obj === "function";
        };
    }
    if (!$.type) {
        $.type = function (obj) {
            if (obj == null) {
                return String(obj);
            }
            if (typeof obj !== "object" && typeof obj !== "function") {
                return typeof obj;
            }
            return Object.prototype.toString.call(obj)
                .slice(8, -1).toLowerCase();
        };
    }
})(jQuery);
