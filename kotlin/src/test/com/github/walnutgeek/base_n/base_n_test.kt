package com.github.walnutgeek.base_n

import org.junit.Test
import kotlin.test.assertEquals

class BaseNTest {
    @Test
    fun testAssert() {
        val alphabet = Alphabet("abc")
        assertEquals("abc", alphabet.key)
        assertEquals(55451, alphabet.encode_direction.from_log)
        assertEquals(10986, alphabet.encode_direction.to_log)
    }
}
