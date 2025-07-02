odoo.define('winpos_search_mst_parner.auto_captcha', function (require) {
    "use strict";
    const FormController = require('web.FormController');

    FormController.include({
        _loadRecord: async function () {
            await this._super.apply(this, arguments);
            // Chỉ tự động gọi khi model là res.partner và có trường captcha_img
            if (this.modelName === 'res.partner' && this.renderer.state.data.id) {
                this._rpc({
                    model: 'res.partner',
                    method: 'get_captcha',
                    args: [[this.renderer.state.data.id]],
                }).then(() => {
                    // Reload lại record để cập nhật ảnh captcha mới
                    this.reload();
                });
            }
        },
    });
});