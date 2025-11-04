#!/usr/bin/env bash
set -e
DB=bhz_dev
CONTAINER=odoo-bhz_odoo_1
COMMON_ARGS="--db_host=db --db_user=odoo --db_password=odoo --without-demo true --log-level debug --stop-after-init"

# ajuste a lista conforme necessário
MODULES=(
  bhz_delivery_superfrete
  bhz_marketplace_base
  bhz_marketplace_magalu
  bhz_marketplace_meli
  bhz_payment_multi
  bhz_hr_attendance_idcontrol
  bhz_stock_supplier_label
)

for mod in "${MODULES[@]}"; do
  echo "=== Instalando/Atualizando: $mod ==="
  if ! podman exec -it "$CONTAINER" bash -lc "odoo -d $DB -i $mod $COMMON_ARGS" ; then
    echo ""
    echo ">>> FALHOU em: $mod"
    echo "Mostrando as últimas linhas do erro acima."
    exit 1
  fi
  echo "OK: $mod"
done

echo "=== Tudo instalado com sucesso ==="
