export interface IceChunk { isReasoning: boolean; content: string; }
export class IceStreamParser {
    public parseChunk(chunk: string): IceChunk {
        if (chunk.includes("<reasoning>")) {
            return { isReasoning: true, content: chunk.replace(/<reasoning>|<\/reasoning>/g, "") };
        }
        return { isReasoning: false, content: chunk };
    }
}
