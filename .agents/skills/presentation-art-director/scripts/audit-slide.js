// Run inside use_figma. Pass two corresponding slide frame IDs and the current register.
async function auditSlide(sourceId, targetId, blocks = []) {
  if (sourceId === targetId) throw new Error("Expected a separate copy");
  async function tree(id) {
    const frame = await figma.getNodeByIdAsync(id);
    if (!frame || frame.type !== "FRAME") throw new Error("Missing slide " + id);
    const nodes = new Map();
    function visit(node) {
      nodes.set(node.id, node);
      for (const child of node.children || []) visit(child);
    }
    visit(frame);
    return nodes;
  }
  const source = await tree(sourceId);
  const target = await tree(targetId);
  const covered = new Set();
  const mapped = new Set();
  const issues = [];
  const review = [];
  for (const block of blocks) {
    const ids = block.sourceIds || [];
    const result = (block.targetIds || []).map(id => target.get(id));
    if (!ids.length || !block.reason || !["keep","composite","remove"].includes(block.action))
      issues.push(["decision", ids[0]]);
    for (const id of ids) {
      if (!source.has(id) || covered.has(id)) issues.push(["invalid-source", id]);
      covered.add(id);
    }
    if (result.some(n => !n) || (!result.length && block.action !== "remove"))
      issues.push(["invalid-target", ids[0]]);
    for (const n of result) if (n) mapped.add(n.id);
    if (block.action === "composite" && !result.some(n =>
      n && Array.isArray(n.fills) && n.fills.some(f => f.visible !== false && f.type === "IMAGE" && f.imageHash)))
      issues.push(["missing-raster", ids[0]]);
    if (block.role === "text" && !result.some(n => n && n.type === "TEXT"))
      issues.push(["missing-live-text", ids[0]]);
    if (block.role === "rect-image" && !result.some(n => n && n.type === "FRAME" &&
      n.clipsContent && n.children.some(c => c.visible && Array.isArray(c.fills) &&
      c.fills.some(f => f.type === "IMAGE" && f.visible !== false && f.imageHash))))
      issues.push(["image-container", ids[0]]);
    if (!block.role || !block.structureEvidence || !block.renderEvidence)
      issues.push(["missing-evidence", ids[0]]);
  }
  for (const id of source.keys()) if (!covered.has(id)) issues.push(["unmapped-source", id]);
  for (const [id,n] of target) {
    if (!mapped.has(id)) issues.push(["unmapped-target", id]);
    const effects = (n.effects || []).filter(e => e.visible !== false).map(e => e.type);
    const gradients = Array.isArray(n.fills) ? n.fills.filter(f => f.visible !== false && f.type.startsWith("GRADIENT")).map(f => f.type) : [];
    if (effects.length || gradients.length || n.visible === false)
      review.push({id, effects, gradients, hidden:n.visible === false});
  }
  return {sourceId,targetId,issues,review};
}
