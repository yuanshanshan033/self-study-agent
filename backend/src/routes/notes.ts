import { Router } from "express";
import { getNotes, getNoteById } from "../db/sqlite";

export const notesRouter = Router();

notesRouter.get("/", (req, res) => {
  const page = parseInt(req.query.page as string) || 1;
  const pageSize = parseInt(req.query.pageSize as string) || 20;
  const result = getNotes(page, pageSize);
  res.json(result);
});

notesRouter.get("/:id", (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "Invalid note ID" });
    return;
  }
  const note = getNoteById(id);
  if (!note) {
    res.status(404).json({ error: "Note not found" });
    return;
  }
  res.json(note);
});

export default notesRouter;