export interface TaskDocumentReference {
  id: string;
  title: string;
}

interface TaskDocumentApi {
  list: (params: { project_id: string; page_size: number }) => Promise<{
    documents?: Array<{ id: string; title?: string | null }>;
  }>;
  get: (id: string, projectId: string) => Promise<{ id?: string; title?: string | null }>;
}

export function resolveTaskDocumentTitle(
  documents: TaskDocumentReference[],
  documentId: string,
  loading: boolean,
): string {
  const title = documents.find((document) => document.id === documentId)?.title?.trim();
  if (title) return title;
  return loading ? "Loading document title…" : "Document unavailable";
}

export async function loadTaskDocumentReferences(
  api: TaskDocumentApi,
  projectId: string,
  attachedIds: string[],
): Promise<TaskDocumentReference[]> {
  const uniqueAttachedIds = [...new Set(attachedIds.filter(Boolean))];
  let listed: TaskDocumentReference[] = [];
  try {
    const response = await api.list({ project_id: projectId, page_size: 100 });
    listed = (response.documents || [])
      .filter((document) => document.id)
      .map((document) => ({ id: document.id, title: document.title || "" }));
  } catch {
    // Individual lookups below still give reopened attachments a chance to resolve.
  }

  const listedIds = new Set(listed.map((document) => document.id));
  const missingIds = uniqueAttachedIds.filter((id) => !listedIds.has(id));
  const fetched = await Promise.all(
    missingIds.map(async (id) => {
      try {
        const document = await api.get(id, projectId);
        return document.id
          ? { id: document.id, title: document.title || "" }
          : null;
      } catch {
        return null;
      }
    }),
  );

  return [...listed, ...fetched.filter((document): document is TaskDocumentReference => document !== null)];
}
