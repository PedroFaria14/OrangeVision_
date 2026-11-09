// null: ainda não houve escolha explícita; uma opção pode ser pré-selecionada.
export function authorizedDeviceId(
  selection: string | null,
  options?: readonly { id: string }[],
) {
  if (!options) return '';
  if (selection === null && options.length === 1) return options[0].id;
  return options.some((item) => item.id === selection) ? (selection ?? '') : '';
}
