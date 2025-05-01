<p align="center">
  <img src="https://info.mollie.com/hubfs/github/odoo/logo.png" width="128" height="128"/>
</p>
<h1 align="center">Mollie addon for Odoo 16</h1>

A submodule of our [Odoo](https://github.com/yobst/odoo) repository. Each subfolder in this repository corresponds to a module in Odoo.

## How to configure

- Set up Git submodule:
``` sh
git submodule init mollie/mollie-odoo
git submodule update mollie/mollie-odoo

```
- Install the python dependencies: `pip install -r requirements.txt`.
- Activate the needed Mollie module(s) in your Odoo instance.
- Open the **Point of Sale** module.
- Go to **Configuration > Settings**. Enter the API key under **Mollie Terminal Api Key** in the **Payment Terminls** section. 
- Go to **Configuration > Mollie Pos Terminal**, and sync terminals.
- Go to **Configuration > Payment Methods**, and create a payment method corresponding to each Mollie terminal to be used.

Learn more: https://apps.odoo.com/apps/modules/16.0/payment_mollie_official/
