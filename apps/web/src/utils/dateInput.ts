function formatDate(year: number, month: number, day: number): string | null {
  if (year < 1900 || month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }
  const dt = new Date(year, month - 1, day);
  if (dt.getFullYear() !== year || dt.getMonth() !== month - 1 || dt.getDate() !== day) {
    return null;
  }
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function normalizeDateText(raw: string | null | undefined): string | null {
  if (!raw) {
    return null;
  }
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 8) {
    return formatDate(
      Number(digits.slice(0, 4)),
      Number(digits.slice(4, 6)),
      Number(digits.slice(6, 8)),
    );
  }
  if (digits.length === 6) {
    return formatDate(
      2000 + Number(digits.slice(0, 2)),
      Number(digits.slice(2, 4)),
      Number(digits.slice(4, 6)),
    );
  }
  return null;
}
