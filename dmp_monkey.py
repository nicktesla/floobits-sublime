from lib import diff_match_patch as dmp

def patch_apply(self, patches, text):
    """Merge a set of patches onto the text.  Return a patched text, as well
    as a list of true/false values indicating which patches were applied.

    Args:
      patches: Array of Patch objects.
      text: Old text.

    Returns:
      Two element Array, containing the new text and an array of boolean values.
    """
    if not patches:
        return (text, [], [])

    # Deep copy the patches so that no changes are made to originals.
    patches = self.patch_deepCopy(patches)

    text_len = len(text)
    nullPadding = self.patch_addPadding(patches)
    text = nullPadding + text + nullPadding
    self.patch_splitMax(patches)

    # delta keeps track of the offset between the expected and actual location
    # of the previous patch.  If there are patches expected at positions 10 and
    # 20, but the first patch was found at 12, delta is 2 and the second patch
    # has an effective expected position of 22.
    delta = 0
    results = []
    positions = []
    for patch in patches:
        position = [3, 0, ""]
        expected_loc = patch.start2 + delta
        text1 = self.diff_text1(patch.diffs)
        end_loc = -1
        if len(text1) > self.Match_MaxBits:
        # patch_splitMax will only provide an oversized pattern in the case of
        # a monster delete.
            start_loc = self.match_main(text, text1[:self.Match_MaxBits],
                                        expected_loc)
            if start_loc != -1:
                end_loc = self.match_main(text, text1[-self.Match_MaxBits:],
                    expected_loc + len(text1) - self.Match_MaxBits)
                if end_loc == -1 or start_loc >= end_loc:
                    # Can't find valid trailing context.  Drop this patch.
                    start_loc = -1
        else:
            start_loc = self.match_main(text, text1, expected_loc)
        if start_loc == -1:
            # No match found.  :(
            results.append(False)
            # Subtract the delta for this failed patch from subsequent patches.
            delta -= patch.length2 - patch.length1
        else:
            # Found a match.  :)
            results.append(True)
            delta = start_loc - expected_loc
            if end_loc == -1:
                text2 = text[start_loc: start_loc + len(text1)]
            else:
                text2 = text[start_loc: end_loc + self.Match_MaxBits]
            if text1 == text2:
                # Perfect match, just shove the replacement text in.
                print "perfect match"
                replacement_str = self.diff_text2(patch.diffs)
                text = (text[:start_loc] + replacement_str +
                            text[start_loc + len(text1):])
                position = [start_loc, len(text1), str(replacement_str)]
            else:
                print "imperfect match"
                # Imperfect match.
                # Run a diff to get a framework of equivalent indices.
                diffs = self.diff_main(text1, text2, False)
                if (len(text1) > self.Match_MaxBits and
                    self.diff_levenshtein(diffs) / float(len(text1)) >
                    self.Patch_DeleteThreshold):
                    # The end points match, but the content is unacceptably bad.
                    results[-1] = False
                else:
                    self.diff_cleanupSemanticLossless(diffs)
                    index1 = 0
                    delete_len = 0
                    inserted_text = ""
                    for (op, data) in patch.diffs:
                        if op != self.DIFF_EQUAL:
                            index2 = self.diff_xIndex(diffs, index1)
                        if op == self.DIFF_INSERT:  # Insertion
                            text = text[:start_loc + index2] + data + text[start_loc +
                                                                           index2:]
                            inserted_text += data
                        elif op == self.DIFF_DELETE:  # Deletion
                            diff_index = self.diff_xIndex(diffs, index1 + len(data))
                            text = text[:start_loc + index2] + text[start_loc +
                                diff_index:]
                            delete_len += (diff_index - index2)
                        if op != self.DIFF_DELETE:
                            index1 += len(data)
                    print "cleaned up sematic lossless"
                    position = [start_loc, delete_len, inserted_text]

        print "before", position
        if position[0] < 4:
            position[1] -= 4 - position[0]
            position[2] = position[2][4 - position[0]:]
            position[0] = 0
        else:
            position[0] -= 4

        extra_bytes = len(text) - position[0] - len(position[2])
        print extra_bytes, "extra bytes"
        if extra_bytes <= 4:
            position[1] -= extra_bytes
            position[2] = position[2][:-1 * extra_bytes]

        positions.append(position)
        print "pos", position
    # Strip the padding off.
    text = text[len(nullPadding):-len(nullPadding)]
    print "returning patches. null padding is", len(nullPadding)
    return (text, results, positions)

def monkey_patch():
    dmp.diff_match_patch.patch_apply = patch_apply
