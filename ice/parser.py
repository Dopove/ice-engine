# SPDX-License-Identifier: MIT

class IceStreamParser:
    def parse_chunk(self, chunk):
        """
        Parses a chunk of text for reasoning tags.
        """
        if "<reasoning>" in chunk:
            return {"is_reasoning": True, "content": chunk.replace("<reasoning>", "").replace("</reasoning>", "")}
        return {"is_reasoning": False, "content": chunk}
