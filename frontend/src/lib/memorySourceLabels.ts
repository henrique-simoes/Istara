export interface MemorySourceDocument {
  title?: string | null;
  file_name?: string | null;
  file_path?: string | null;
}

function sourceBasename(source: string): string {
  const normalized = source.replaceAll("\\", "/");
  return normalized.split("/").pop() || normalized;
}

/**
 * Return a user-facing label without discarding the canonical source value.
 * Managed upload paths are implementation details (and often contain UUIDs),
 * so prefer the registered document title and filename while retaining the
 * source string for filtering and deletion operations.
 */
export function memorySourceLabel(
  source: string,
  documents: readonly MemorySourceDocument[],
): string {
  const basename = sourceBasename(source);
  const document = documents.find((candidate) => {
    const filePath = candidate.file_path?.trim();
    const fileName = candidate.file_name?.trim();
    return (
      (filePath && (source === filePath || source.endsWith(`/${filePath}`))) ||
      (fileName && (basename === fileName || source.includes(`/${fileName}`)))
    );
  });

  if (!document) return basename;

  const title = document.title?.trim();
  const fileName = document.file_name?.trim() || basename;
  if (title && fileName && title !== fileName) return `${title} (${fileName})`;
  return title || fileName;
}
